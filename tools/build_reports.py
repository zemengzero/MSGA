"""Build course reports from current code and measured evidence."""

import ast
import csv
import html
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fitz
from docx import Document
from report_diagram import make_architecture
from report_io import Paper, render_docx, render_html

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/generated"
OUT.mkdir(parents=True, exist_ok=True)
REPO = "https://github.com/IceApplejuice/zhiyeteam-software-engineering"
DATE = "2026-11-01"


def load(name):
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def function_location(module, qualname):
    path = ROOT / "src/zhiyeteam" / (module + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parts = qualname.split(".")
    nodes = tree.body
    node = None
    for part in parts:
        node = next(
            n
            for n in nodes
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part
        )
        nodes = node.body
    return path.relative_to(ROOT).as_posix(), node.lineno, node.end_lineno


FEATURES = [
    (
        "T01 新建与持久保存",
        "store",
        "NoteStore.save",
        "test_store",
        "正文、标签、关联和历史在一个事务内；UI调用NotebookApp.save",
    ),
    (
        "T02 事务与并发冲突",
        "store",
        "NoteStore._write",
        "test_store/test_links",
        "BEGIN IMMEDIATE先取写锁，expected_revision校验旧窗口，异常回滚",
    ),
    (
        "T03 关键词与标签搜索",
        "search",
        "search_notes",
        "test_search",
        "关键词/标签AND、中文子串、ASCII大小写，标题命中优先",
    ),
    (
        "T04 稳定双链与反向引用",
        "links",
        "extract_links",
        "test_links",
        "UUID作为身份，排除代码和转义，backlinks按有效来源计数",
    ),
    (
        "T05 回收站与恢复",
        "store",
        "NoteStore.set_deleted",
        "test_history",
        "删除标记不换UUID，永久删除须先进入回收站",
    ),
    (
        "T06 历史版本回退",
        "store",
        "NoteStore.restore_version",
        "test_history",
        "回退旧内容通过save生成新revision，旧记录保留",
    ),
    (
        "T07 完整备份",
        "backup",
        "create_backup",
        "test_backup",
        "SQLite在线备份、临时目标、校验后发布，已存在目标不覆盖",
    ),
    (
        "T08 受保护恢复",
        "backup",
        "restore_backup",
        "test_backup",
        "先校验、先保护当前库、再替换，失败回退，回退失败禁写",
    ),
    (
        "T09 Markdown导入",
        "transfer",
        "import_markdown",
        "test_transfer",
        "严格UTF-8/BOM，逐项报告，同名导入重命名",
    ),
    (
        "T10 离线导出与安全",
        "transfer",
        "export_notes",
        "test_transfer",
        "本地文件链接，HTML白名单去脚本/远程图/危险URI，导出空目录",
    ),
    (
        "T11 桌面与未保存守卫",
        "ui",
        "NotebookApp.guard",
        "test_ui_guard/gui_smoke",
        "真实Tk窗口，离开/退出确认时暂停自动保存",
    ),
    (
        "T12 本地部署与启动",
        "__main__",
        "main",
        "frozen_smoke",
        "独立exe启动、演示库与正式库分离；不依赖网络服务",
    ),
]


def build():
    tests = load("test_results.json")
    gui = load("gui_smoke.json")
    frozen = load("frozen_smoke.json")
    binary = load("build.json")
    assert tests["passed"] and gui["passed"] and frozen["passed"]
    moment = (
        datetime.fromisoformat(tests["executed_at_utc"])
        .astimezone(timezone(timedelta(hours=8)))
        .strftime("%Y-%m-%d %H:%M:%S 北京时间")
    )
    rows = []
    md = ["# 演示功能与代码定位", "", f"代码链接对应发布标签v1.0.0；仓库：{REPO}。", ""]
    for rid, module, fn, case, explain in FEATURES:
        path, start, end = function_location(module, fn)
        rows.append((rid, path + ":" + str(start), fn, case + "；" + explain))
        md.extend(
            [
                f"## {rid}",
                "",
                f"入口：[{path}:{start}]({REPO}/blob/v1.0.0/{path}#L{start})，函数`{fn}`。",
                f"验证：`{case}`。{explain}",
                "",
            ]
        )
    (ROOT / "docs/功能与代码定位.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "reports/code_map.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    p = Paper(
        "知页软件工程团队项目实验报告", f"选题 需求分析 设计 测试｜团队版1.0.0｜{DATE}"
    )
    p.p(
        "小组规模4人，暂用A/B/C/D标记；默认A为赵钦泽/IceApplejuice，其他成员的真实姓名、学号、账号需本人补充。下文区分已运行的基础软件、已执行的测试和仍待成员完成的增量/反馈，不虚构四人的开发经历。正式验收日期以老师最新课堂通知为准，计划按最紧的11月2日准备。"
    )
    p.h("一 选题与NABCD")
    p.p(
        "选题为“知页·本地学习知识库”，面向学生与个人知识工作者。验收主线是记录→搜索→关联→版本回退→误删恢复→完整备份，重点展示可验证的数据保护和清楚的模块边界。它是本机可运行的桌面程序，演示视频不能替代实体运行。"
    )
    p.table(
        ["维度", "本项目回答"],
        [
            (
                "Need",
                "学习笔记分散、难以按概念找回；改名或误删后关联与内容难恢复。这是本项目的场景假设，尚未以真人访谈统计证明。",
            ),
            (
                "Approach",
                "本地桌面编辑、关键词/标签AND检索、UUID双链、版本历史、回收站及SQLite完整备份；界面/规则/存储分开实现。",
            ),
            (
                "Benefit",
                "无网络账号也能记录与查找；关联不随标题改变而丢失；恢复流程有明确保护副本和失败分支。节约时间/满意度尚未真人量化。",
            ),
            (
                "Competitors",
                "替代方案包括普通文本编辑器、云端笔记及成熟Markdown知识库。本项目优于纯文本的部分是关联和恢复闭环；不声称功能全面胜过成熟产品，也不杜撰价格或调研数据。",
            ),
            (
                "Delivery",
                "GitHub托管源码与真实版本记录，Release分发Windows exe、文档和操作步骤；安排同学真实试用并形成反馈Issue。仓库当前私有，教师/成员访问权限需所有者实际配置。",
            ),
        ],
    )
    p.h("二 需求分析")
    p.p(
        "团队版独立维护T01–T12需求，不把个人实验1/2中全部设计直接宣称为已实现。容量边界：每篇正文UTF-8≤1MiB，标题1–80字符，最多20个标签且每个≤20字符；active最多5000篇，数据库含历史设置256MiB页数上限。各项约束同时生效，历史也消耗空间；容量不足时保存失败并保留编辑器内容。"
    )
    p.table(
        ["编号与需求", "规则与验收入口"],
        [(a, e + "；验证见" + d) for a, b, c, d, e in FEATURES],
    )
    p.p(
        "非功能范围：离线运行；SQLite事务避免正文/标签/关联/历史混组；搜索结果确定排序；未保存状态明确；备份输入先验证再改当前库；Windows独立exe可启动。支持Markdown文本编辑及常用阅读样式，完整表格通过HTML导出阅读；不宣称内置阅读视图完整兼容CommonMark。"
    )
    p.p(
        "本版不提供多人实时协作、云同步、移动端、图片附件管理、加密库或复杂权限。四人合作是代码开发协作，不等于软件用户端多人共享。这些边界有助于按期形成可验收闭环。"
    )
    p.h("三 概要设计与技术栈")
    p.figure(
        make_architecture(ROOT),
        "当前实际模块与调用分层：界面调用业务与查询，全部业务数据使用同一个SQLite库。",
    )
    p.table(
        ["层/模块", "职责与实际技术"],
        [
            (
                "桌面入口与视图",
                "Python 3.13.3、Tkinter/ttk；__main__.py解析数据目录和演示参数，ui.py处理事件、状态、预览和未保存确认。",
            ),
            (
                "领域与数据",
                "models.py冻结Note快照和校验错误；store.py持久化与revision检查；SQLite3.49.1为唯一权威源。",
            ),
            (
                "查询与知识关联",
                "search.py处理AND、排序；links.py共用识别器排除代码/转义并生成反向关联。",
            ),
            (
                "迁移与恢复",
                "transfer.py导入和安全HTML导出，Python-Markdown3.10.2解析后白名单输出；backup.py在线备份、结构/完整性校验及保护恢复。",
            ),
            (
                "测试与发行",
                "unittest、故障注入、真实Tk控件冒烟、打包exe冒烟；PyInstaller6.22.3在Windows生成单文件程序；GitHub Actions执行测试。",
            ),
        ],
    )
    p.p(
        "运行调用：Tk按钮/快捷键→NotebookApp事件→NoteStore或search/links/transfer/backup模块→SQLite/用户选择的本地文件。视图没有自己的SQL副本；导出HTML只是本地阅读制品，不启动服务器。数据默认保存在当前用户LOCALAPPDATA/ZhiYeTeam/personal，--demo使用独立演示库。"
    )
    p.h("四 数据 事务与关键流程")
    p.table(
        ["数据表", "关键字段与约束"],
        [
            (
                "notes",
                "id UUID主键，title、body、created_at、updated_at、revision≥1、deleted=0/1。标题可重名，身份不依赖标题。",
            ),
            (
                "tags / note_tags",
                "tags.name唯一；note_tags(note_id,tag_id)复合主键，外键绑定笔记；NFC与ASCII小写去重。",
            ),
            (
                "links",
                "(source_id,target_id)复合主键，occurrences>0；source外键，target不设外键，允许目标失效而保留源标记。",
            ),
            (
                "history",
                "(note_id,revision)唯一，保存标题/正文/tags_json、时间、action；普通编辑、删除/恢复和回退均可追溯。",
            ),
            (
                "settings",
                "key/value；供编辑器参数等库内设置使用，本版尚未提供完整设置面板，列为A增量任务。",
            ),
        ],
    )
    p.p(
        "保存：校验输入→BEGIN IMMEDIATE取得写锁→读取当前revision并核对expected_revision→更新正文/标题、标签、关联和历史→一次COMMIT；失败ROLLBACK。仅在提交成功后清除dirty。注入关联写失败的测试验证正文及版本不会部分更新；旧窗口保存由冲突测试验证。"
    )
    p.p(
        "关联：正文保存[[note:UUID]]，预览按当前标题显示；别名可选。解析器与导出/图谱复用同一extract_links。目标改名UUID不变，删除后标记不可用，恢复同UUID重新可达；代码中的示例标记不计入真实引用。"
    )
    p.p(
        "版本/回收站：回退不是覆盖旧历史，而是读取旧行后新建revision。删除先标记deleted，恢复沿用原ID；永久删除仅允许对回收站执行，清理该笔记历史和源引用，其他笔记中的失效目标仍保留。旧备份可能含已删除内容，不声称安全擦除。"
    )
    p.p(
        "备份恢复：在线backup创建临时SQLite文件→校验应用标识、版本、Schema与完整性→发布。恢复前验证输入并生成当前库保护副本，再复制快照；失败先回退，回退也失败则禁写并显示保护位置。结构与完整性校验不等于来源防伪认证。"
    )
    p.h("五 设计取舍与个人实验衔接")
    p.p(
        "个人实验曾提出.NET/WPF、普通Markdown与catalog.json、跨文件日志协议。团队版为了本次实体验收与四人易于读懂/分工，改用Python/Tkinter和SQLite集中持久化；不再实现JSON与正文双源提交。这个调整是明确的重新选型，不把设计稿当作已经实现的功能。"
    )
    p.table(
        ["选择", "好处", "代价与限制"],
        [
            (
                "桌面本地而非Web服务",
                "离线、不需要现场网络服务与账号",
                "主要在Windows验证，跨系统发行和手机端未验证。",
            ),
            (
                "SQLite权威源",
                "核心写操作可原子提交，备份API能拍一致快照",
                "正文不直接作为散落.md保存，迁移需导出/完整备份。",
            ),
            (
                "UUID而非标题连接",
                "重命名/重名不改变目标",
                "原始文本中的UUID较长；用选择器和阅读视图降低操作负担。",
            ),
            (
                "带保护副本的恢复",
                "可现场验证失败分支和当前数据保留",
                "额外空间与恢复时间，需要用户自己管理旧备份。",
            ),
        ],
    )
    p.h("六 实际测试报告")
    p.p(
        f"执行时间：{moment}。环境：{tests['platform']}，Python {tests['python']}，SQLite {tests['sqlite']}。自动化结果：执行{tests['tests_run']}项，失败{tests['failures']}，错误{tests['errors']}，跳过{tests['skipped']}。原始证据为reports/test_results.json与test-log.txt。"
    )
    p.table(
        ["测试项", "实际结果", "耗时ms"],
        [(c["test"], c["status"], str(c.get("ms", "—"))) for c in tests["cases"]],
    )
    p.p(
        f"性能实测范围：200篇、每篇2048 UTF-8字节，30次后端搜索调用，P95={tests['backend_benchmark']['p95_ms']:.3f}ms，最大={tests['backend_benchmark']['maximum_ms']:.3f}ms。包括存在/不存在/指定topic结果，均校验命中数。不把这个数字冒称完整UI端到端时延或5000篇极限性能。"
    )
    p.p(
        f"真实窗口测试：源程序Tk控件新建/输入/保存/预览检查passed={gui['passed']}；独立程序{frozen['tested_executable']}已实际启动并验证passed={frozen['passed']}。发布文件{binary['file']}，{binary['bytes']}字节；SHA-256={binary['sha256']}。另一台无Python电脑的冷启动属于D增量验收，尚未伪称完成。"
    )
    shot = ROOT / "reports/screenshots/desktop.png"
    if shot.exists():
        p.figure(
            shot,
            "实际程序窗口证据：通过PrintWindow只读取本程序拥有的窗口。画面为合成演示数据，不是用户反馈截图。",
        )
    p.h("七 团队过程与真实记录")
    p.p(
        "基础软件由当前IceApplejuice账号在AI协助下建立，Git每个阶段有真实文件差异与测试。四人的后续增量、姓名/学号、各自账号、PR审核与真人反馈仍需成员本人完成；本报告不把A的记录分摊成B/C/D的贡献。分工与至少三次提交的内容见独立计划文档和GitHub任务卡。"
    )
    p.p(
        "普通Git HTTPS在本机网络无法连通时，使用Git Data API搬运现有本地对象；对齐作者、邮箱、实际日期、树和消息。是否保持原提交SHA以reports/github_publish.json的真实结果为准，不重写为其他成员身份或修改开发日期。仓库使用私有可见性，课堂检查前需解决教师访问权限。"
    )
    p.h("八 反馈 已知限制与后续工作")
    p.p(
        "目前没有真人试用记录，反馈CSV只有表头；演示数据和自动截图不能计作用户反馈。建议两位组外同学各完成“新建→搜索→回退→备份恢复”，记录原话、实际问题和经同意的证据，形成Issue并回归。若未发现缺陷应据实记录，不杜撰满意度或访谈。"
    )
    p.p(
        "已知限制：原生阅读视图是常用Markdown样式子集；没有附件、同步、加密及手机端；无完整设置面板与自动周期备份；当前实际验证系统为本机Windows11。大库历史占用、窄窗口/长文交互和跨机启动需按分工继续验证。任何新功能未通过回归不并入验收主干。"
    )

    plan = Paper(
        "知页四人分工与GitHub提交计划", f"待成员认领的实际增量｜至少3次/人｜{DATE}"
    )
    plan.p(
        "计划不是已完成记录。四人姓名/学号/账号须对应真实身份；现有基线账号的开发记录不代替另外三位。若按明天11月2日验收，执行短周期方案；若实际为11月9日，再做扩展版任务。"
    )
    plan.table(
        ["成员", "主要文件与责任", "三次短周期提交"],
        [
            (
                "A 默认赵钦泽/IceApplejuice",
                "ui.py、__main__.py；统筹主干和实体演示",
                "①字号设置持久化；②长文滚动/窄窗口；③新增交互测试和手册。",
            ),
            (
                "B 待补真实姓名账号",
                "store.py、backup.py、schema.sql；数据可靠性",
                "①备份空间预检；②恢复审计不记正文；③空间/审计/回退回归测试。",
            ),
            (
                "C 待补真实姓名账号",
                "search.py、links.py、transfer.py；查找与关联",
                "①更新时间过滤；②命中摘要；③日期/摘要/转义边界测试。",
            ),
            (
                "D 待补真实姓名账号",
                "tests/、tools/、.github/；验证发布与报告",
                "①CI结果工件；②发行清单和第二台电脑验证；③真实反馈修复/回归与最终报告。",
            ),
        ],
    )
    plan.h("提交内容与验收证据")
    plan.p(
        "每人建立feature/a-…、feature/b-…、feature/c-…或test/d-…分支。每次提交的正文写目的、实际变更、运行命令、结果和限制；每次都有实质diff。A协调ui入口，其他成员优先新增独立模块，避免同一函数被三人同时重写。完整的12项扩展任务及提交标题见仓库docs/团队分工与提交计划.md。"
    )
    plan.table(
        ["步骤", "成员本人必须做的操作"],
        [
            (
                "身份",
                "所有者邀请其余真实GitHub账号并由本人接受；git本地邮箱须关联本人GitHub，不能全用组长配置。",
            ),
            (
                "实现",
                "从最新main开分支；实际修改、运行测试、检查git diff后commit，再push。不能用空提交或改作者凑次数。",
            ),
            (
                "评审",
                "PR写功能/文件/验证/限制，由另一人看diff并试用。保留可核验提交/PR记录，合并时注意作者归属。",
            ),
            (
                "现场",
                "展示该成员真实commit/diff和一段自己能解释的函数，再运行对应功能；报告中未完成任务保持计划状态。",
            ),
        ],
    )
    plan.h("倒排安排")
    plan.p(
        "今晚先确保四台电脑至少能运行冻结基线；四人各读负责函数10分钟，再独立做短增量。课前2小时停止加功能并回归、打包；课前1小时用演示电脑冷启动、断网走8分钟步骤。长周期任务未完成不合并，防止临时破坏已可运行主干。"
    )
    plan.p(
        "若验收在11月9日：第1–2天增量，第3–4天集成测试，第5天真人试用，第6天修复冻结，第7天演练。日期以老师实际通知为准；不倒填commit日期。"
    )
    plan.h("扩展方向")
    plan.p(
        "A完善字体/焦点/滚动；B增加用户可选周期备份和受确认的历史清理策略；C做失效链接检测与修复；D完善CI工件、发布门禁、跨机测试和反馈闭环。这些是后续真实可提交功能，不宣称已在基线交付。"
    )

    guide = Paper(
        "知页现场演示与代码答辩手册", f"8分钟实体演示｜代码位置自动从AST提取｜{DATE}"
    )
    guide.p(
        "先使用release中的独立exe，不依赖视频、联网安装或开发工具。演示库与正式库分离；不要展示个人正式笔记。现场打开仓库代码或已下载源码，按以下流程指明入口、业务和测试。"
    )
    guide.table(
        ["时间/主讲", "操作", "重点"],
        [
            (
                "0:00–2:00 A",
                "启动、新建、输入保存、重开验证",
                "说清需求与本地边界；从UI.save指到Store.save。",
            ),
            (
                "2:00–3:20 C",
                "关键词/标签查找，关联跳转，目标改名",
                "解释AND/排序和UUID身份，别名与标题不同。",
            ),
            (
                "3:20–4:40 B",
                "保存两版、回退旧版、误删恢复",
                "旧历史不覆盖，恢复仍是同一UUID。",
            ),
            (
                "4:40–6:10 B",
                "备份→新加临时笔记→恢复",
                "活动库完整替换，但先产生保护副本；失败不虚报成功。",
            ),
            (
                "6:10–8:00 D/全员",
                "HTML离线阅读、坏备份拒绝、真实测试和个人PR",
                "区分自动化/真人反馈；每人用自己的diff解释功能。",
            ),
        ],
    )
    guide.h("功能与代码定位")
    guide.table(["功能", "实际文件:行号", "函数", "验证与解释"], rows)
    guide.h("问答提纲")
    guide.table(
        ["老师可能问", "答题要点"],
        [
            (
                "这个功能是哪段代码？",
                "先定位UI事件，再给业务函数和测试；不要只报一个文件名。表中行号来自当前源代码AST，发布标签固定后便于核验。",
            ),
            (
                "为什么选择这个架构？",
                "离线桌面可直接验收；UI与持久化分开，SQLite集中事务减少多文件一致性风险；与个人实验的技术调整已明确记录。",
            ),
            (
                "数据库事务到底包括什么？",
                "写锁先于revision检查；正文、标签、关联、历史一起提交。注入关联写失败时，正文与版本回滚的测试就是证据。",
            ),
            (
                "改名/删除后关联怎么办？",
                "UUID决定身份，标题动态显示；删除目标不删源标记，回收站恢复原ID可重新跳转。",
            ),
            (
                "版本回退会丢历史吗？",
                "旧版本读取后走正常save生成新revision，原history行不覆盖。",
            ),
            (
                "恢复失败怎么保护？",
                "先校验输入和保护当前库；失败回退保护副本，回退失败就禁止写入，用户还能另存编辑器内容。",
            ),
            (
                "每个人做了什么？",
                "展示本人真实账号记录、diff、PR、测试与能讲解的代码。计划未执行就说尚未执行，不能把现有基线署给四人。",
            ),
            (
                "这个测试结果证明什么？",
                "30项单元/业务测试和exe窗口冒烟已运行；200篇后端检索P95不是全UI性能；跨机和真人试用没有做就不算通过。",
            ),
        ],
    )

    manual = Paper("知页用户操作手册", f"Windows独立桌面版1.0.0｜{DATE}")
    manual.p(
        "解压Windows发布包，双击“启动演示.bat”体验独立演示库；双击ZhiYeTeam.exe或“启动个人笔记.bat”进入正式个人库。不需要先安装Python。不要在压缩包预览窗口直接运行。首次现场验收前，请在验收电脑实际打开一次。"
    )
    manual.table(
        ["操作", "步骤"],
        [
            (
                "记录",
                "点新建，输入标题和正文；标签以逗号分隔。Ctrl+S保存；静止输入约1.2秒自动尝试保存，持续编辑另每10秒尝试。失败时保留未保存提示和编辑器内容。",
            ),
            (
                "查找",
                "左侧关键词同时查标题/正文；多个词、多个标签都取AND。清空条件回到全部笔记；标题命中优先，随后按修改时间倒序。",
            ),
            (
                "关联",
                "点插入关联并选目标；阅读视图点击关联跳转。链接存UUID，标题可改变；代码块和转义示例不计为实际引用。",
            ),
            (
                "回退",
                "历史版本中选择旧内容，点恢复；回退会生成新版本，现有历史仍保留。",
            ),
            (
                "误删",
                "移入回收站后可恢复；永久删除只针对回收站并需确认，旧备份可能保留它。",
            ),
            (
                "备份",
                "选择创建完整备份并指定新文件名。目标已存在不会覆盖；备份包含笔记、标签、关联、版本和回收站。",
            ),
            (
                "恢复",
                "选择备份，核对数量并确认；系统先保存当前库保护副本再恢复。完成提示给保护位置；失败查看提示，不继续对未知状态强写。",
            ),
            (
                "迁移",
                "导入选择UTF-8 .md，错误逐项列出；导出选择空目录，可出Markdown或静态HTML，HTML从index.html打开。图片附件本版不处理。",
            ),
        ],
    )
    manual.p(
        "数据位置：默认LOCALAPPDATA/ZhiYeTeam/personal/notes.db；演示库为同级demo目录。数据库通过SQLite管理，不要直接修改表或用其他文件替换运行中的数据库。需要迁移使用导出或完整备份。未保存冲突可从“更多→当前编辑内容另存为文件”保留缓冲。"
    )
    manual.p(
        "本版只验证本机Windows11；其他Windows电脑需实际试运行。没有云同步、多人共享或加密，不把工具当作密码保险箱。使用真实反馈记录表时，由参与者实际操作并同意记录，软件截图本身不是用户反馈。"
    )

    papers = [
        ("01_团队项目实验报告", p),
        ("02_四人分工与提交计划", plan),
        ("03_现场演示与代码答辩", guide),
        ("04_用户操作手册", manual),
    ]
    for name, paper in papers:
        render_docx(paper, OUT / (name + ".docx"))
        render_html(paper, OUT / (name + ".html"))
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

    def render(item):
        name, paper = item
        profile = ROOT / "runtime/report-browser" / name
        subprocess.run(
            [
                str(chrome),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                "--allow-file-access-from-files",
                "--user-data-dir=" + str(profile),
                "--print-to-pdf=" + str(OUT / (name + ".pdf")),
                (OUT / (name + ".html")).as_uri(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=True,
        )
        d = Document(OUT / (name + ".docx"))
        dt = "".join(x.text for x in d.paragraphs) + "".join(
            c.text for t in d.tables for row in t.rows for c in row.cells
        )
        pdf = fitz.open(OUT / (name + ".pdf"))
        pt = "".join(pg.get_text() for pg in pdf)
        norm = lambda s: "".join(str(s).split())
        fragments = []
        for k, v in paper.blocks:
            if k == "p":
                fragments.append(v)
            elif k == "h":
                fragments.append(v[0])
            elif k == "figure":
                fragments.append(v[1])
            else:
                fragments.extend(v[0])
                fragments.extend(c for row in v[1] for c in row)
        assert all(norm(s) in norm(dt) and norm(s) in norm(pt) for s in fragments), (
            name + "缺失文本"
        )
        pdf[0].get_pixmap().save(ROOT / "runtime" / (name + "_preview.png"))
        report = {"file": name, "pdf_pages": len(pdf), "word_pdf_content_matches": True}
        pdf.close()
        return report

    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(render, papers))
    (ROOT / "reports/document_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    build()
