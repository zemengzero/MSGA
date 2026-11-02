# C 个人工作说明：搜索增强与知识关联回归

更新日期：2026-11-02。项目：知页·本地学习知识库（`zemengzero/MSGA`）。GitHub：`ZYQY218`。姓名：**万语**；学号：**U202414607**。

当前状态：C1、C2 及极端日期修正已提交并推送至 `feature/c-search-links`；C3 的测试、演示工具和本说明已完成验证，纳入本次交付。统一合并请求为 [PR #14](https://github.com/zemengzero/MSGA/pull/14)，2026-11-02 核实时为 open、尚未合并。日期筛选和摘要**待 D 接入界面**；尚未完成界面验收、跨机验证或整机演示。Issue 认领状态未在本轮核验，不写成已完成。

## 一、我的工作范围和代码位置

| 阶段 | 实际完成内容 | 代码及交付位置 |
| --- | --- | --- |
| C1 | 带时区的可选更新时间过滤、UTC 半开区间、参数校验、旧调用兼容 | `src/zhiyeteam/search.py`；`tests/test_search_extensions.py`；`docs/C1_更新时间过滤交接.md` |
| C2 | `SearchHit`、真实命中字段、纯文本摘要，复用原筛选和排序 | `src/zhiyeteam/search.py`；`src/zhiyeteam/search_presenter.py`；`tests/test_search_hits.py`；`docs/C2_命中字段与摘要交接.md` |
| 后续修正 | UTC 换算超出可表示范围时，将 `OverflowError` 转为含参数名的 `ValidationError` | `_utc_bound` 及两个极端日期回归测试 |
| C3 | 固定时间/UUID 的搜索与关联综合回归；独立合成数据与调用演示；个人说明 | `tests/test_c_search_links_regression.py`；`tools/c_search_demo.py`；本文；`reports/C3_*` |

UUID 双链、改名保持关联、回收站恢复、代码和转义标记排除是项目已有能力。我未修改 `links.py`，C3 通过回归验证这些能力未受搜索扩展影响，不宣称新增链接识别或链接修复功能。共享的 `ui.py`、`backup.py` 和数据库 Schema 均未修改。

## 二、日期语义与兼容策略

`search_notes(store, keywords="", tags=(), deleted=False, *, updated_from=None, updated_before=None)` 保留原有四个位置参数，日期参数仅限关键字传入。返回值仍是 `list[Note]`，旧界面仍可直接读取 `note.id`、`note.title`。

- 日期上下界必须是带时区 `datetime`；转换为 UTC 后比较，完整保留微秒。
- 区间 `[updated_from, updated_before)`：包含起点、不含终点；两端可以独立省略。
- 无时区、错误类型、起点不早于终点以及换算超出 UTC 可表示范围时抛 `ValidationError`。换算后可表示的极端日期继续接受。
- 关键词、多标签、日期条件取 AND。默认排除回收站，`deleted=True` 只查询回收站。
- 保留原排序：标题命中优先，其次更新时间降序，同时间按 ID 升序。无关键词不产生标题命中。

给 D 的日期文案：“开始日期（含当天，YYYY-MM-DD）”“结束日期（含当天，YYYY-MM-DD）”。按北京时间 UTC+08:00 解释；结束日期转为次日零点作为排他上界。选择 2026-11-01 当天时为 `[2026-11-01T00:00:00+08:00, 2026-11-02T00:00:00+08:00)`，等价 UTC `[2026-10-31T16:00:00Z, 2026-11-01T16:00:00Z)`。不能用 23:59:59 替代上界，否则会漏掉带微秒的记录。严格日期解析与完整转参片段见 C1 交接说明。

## 三、摘要规则、新 API 与返回示例

`search_hits` 的参数与 `search_notes` 相同，直接复用它的结果和排序，只增加展示信息。`SearchHit` 是不可变对象，字段为 `note: Note`、`matched_fields: frozenset[str]`、`snippet: str`。

`matched_fields` 包含实际出现任一查询词的 `title` / `body`；空关键词为空集合，标签不算关键词命中。词可分别出现在标题和正文，AND 仍针对完整内容判断。只折叠 ASCII A–Z，与旧搜索一致。

摘要折叠换行和连续空白，去掉首尾空白。最多 120 个 Unicode 码点，省略号 `…` 也计入。短正文保留全文；长正文有命中时围绕最早的正文命中，最多留其前 30 字符，向后截取；无正文命中则取正文开头。空正文返回空字符串。

```python
from datetime import datetime, timedelta, timezone
from zhiyeteam.search import search_hits

beijing = timezone(timedelta(hours=8))
start = datetime(2026, 11, 1, tzinfo=beijing)
before = start + timedelta(days=1)
hits = search_hits(store, "动态规划 AI", ["课程", "ai"],
                   updated_from=start, updated_before=before)
for hit in hits:
    fields_text = "、".join(
        label for field, label in (("title", "标题"), ("body", "正文"))
        if field in hit.matched_fields
    ) or "未指定关键词"
    # 标题：hit.note.title；命中位置：fields_text；摘要：hit.snippet。
    # 点击结果后按 hit.note.id 打开完整正文。使用文本控件显示。
```

三种返回示例（ID 为运行时生成的 UUID，完整实例见 C2 交接说明及演示 JSON）：

| 场景 | `note.title` | `matched_fields` | `snippet` |
| --- | --- | --- | --- |
| 标题命中“动态规划 AI” | 动态规划 AI 提纲 | `frozenset({'title'})` | `记录状态转移。`（7 字符） |
| 长文正文命中，查询词分散 | 长文练习 | `frozenset({'body'})` | `…` + 30 个“甲” + “动态规划” + 84 个“乙” + `…`（120 字符） |
| 空关键词、空正文 | 空正文 | `frozenset()` | 空字符串 |

摘要可能没有显示全部词，这是截取窗口的限制，不能仅凭摘要再判 AND。按码点截取不会切坏 UTF-8 字节，但可能拆开组合字形或 emoji 序列。摘要是普通字符串，不解析 Markdown、不执行 HTML；若 D 改用 HTML 控件，必须按文本转义后显示，不能直接注入。

## 四、验收清单与证据对应

所有测试在独立临时 SQLite 库中运行。C1/C2 原测试固定笔记时间；C3 还固定 `store.now` 和 UUID，确保相同时间的 ID 顺序可复现。不依赖 `sleep` 或运行时钟制造先后。

| 编号 | 覆盖内容 | 对应测试文件/用例 |
| --- | --- | --- |
| C-T01 | 不传日期、原 `Note` 返回和旧顺序；两个 API 一致 | 原 `test_search.py`；`test_search_extensions.py`；`test_search_hits.py` |
| C-T02 | 起点包含、终点排除、微秒 | `test_half_open_interval_includes_microseconds`；C3 `test_combined_filters_keep_title_priority_time_and_id_order` |
| C-T03 | UTC 与 +08:00 等价、北京时间跨日 | `test_equivalent_timezones_and_beijing_midnight`；C3 综合过滤测试 |
| C-T04 | 单端查询；非法类型/无时区/反向与相等区间；UTC 溢出 | `test_search_extensions.py`；`test_search_hits.py` 的非法日期转发测试 |
| C-T05 | 多词、多标签、日期 AND；标题优先与同时间 ID 顺序 | C3 综合过滤及 `test_keywords_split_across_title_and_body_still_form_and` |
| C-T06 | 默认查询、回收站查询和来源恢复后的搜索/反链一致 | `test_deleted_flag_still_selects_trash`；C3 `test_source_trash_restore_keeps_search_and_backlinks_in_sync` |
| C-T07 | 中文、ASCII 大小写、emoji、长文、空正文、字段与长度 | `test_search_hits.py`；C3 综合过滤和分散词测试 |
| C-T08 | 空关键词、无结果、分散多词，不以摘要判断 AND | C3 `test_distant_words_and_empty_query_with_linked_long_body`；`test_search_hits.py` |
| C-T09 | UUID 改名、目标/来源删除恢复；行内代码、两类围栏、奇偶转义、多次真实链接计数 | C3 后四项关联回归；原 `test_links.py` 与 `test_history.py` 均保留并通过 |

## 五、实际运行命令与结果

环境：Windows，Python 3.12.3，项目独立 `.venv`，已按 README 安装项目依赖。工作目录为仓库根目录。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_c_search_links_regression.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/c_search_demo.py --database runtime/c_search_demo/notes_verified.db
```

实际结果：C3 新增 **7 项全部通过**；提交前完整回归 **63 项全部通过**，1.500 秒，退出码 0。完整输出在 `reports/C3_test_results.txt`。C1 的 41 项、C2 的 54 项和极端日期修正后的 56 项日志分别保留，属于各阶段当时的执行记录。

演示脚本实际生成 9 篇合成笔记，输出保存为 `reports/C3_demo_results.json`。本地另用 Python 断言核对输出的 ID 顺序、字段、摘要长度、数据库笔记数量、固定 UTC 微秒时间及真实反向链接计数；再次以同一路径运行时退出码为 2，数据库 SHA-256 未变化。默认临时库模式也已实际运行并通过。核验结果在 `reports/C3_demo_verification.txt`。

这些证据仅代表本机后端自动化及命令行演示，未进行实际日期/摘要界面操作，不等于整机、跨机或真人体验验收。

## 六、给 D 的合成数据与复现方式

工具：`tools/c_search_demo.py`。本地可复用演示库：`runtime/c_search_demo/notes_verified.db`（被 Git 忽略，不作为源码提交）。工具只创建新库，拒绝覆盖已有文件；不指定路径时使用项目 `runtime` 下的临时库，输出后自动清理。

已有库不用重复生成。如需新建持久库，把 `--database` 改为一个尚不存在的路径。所有数据都是合成演示数据，不是真人反馈；笔记创建/修改时间固定，历史记录时间按实际建库过程生成，不用于时间边界验收。UUID 每次建库生成，演示 JSON 提供 key 到实际 UUID 的对应关系。

| key | 数据作用 | 北京时间修改时间 | 预期 |
| --- | --- | --- | --- |
| `title_hit` | 标题“动态规划 AI 提纲”，课程+ai 标签 | 11-01 00:00:00.000000 | 包含起点，标题优先排第一 |
| `body_hit` | 长文中“动态规划”和“AI”分散，真实 UUID 链接指向 target | 11-01 23:59:59.999999 | 排第二，摘要 120 字符；反链计数 1 |
| `before_start` | 起点前一微秒 | 10-31 23:59:59.999999 | 排除 |
| `at_end` | 恰好等于终点 | 11-02 00:00:00.000000 | 排除 |
| `missing_tag` | 仅课程标签 | 11-01 00:00:00 | 因缺 ai 标签排除 |
| `missing_word` | 缺“动态规划” | 11-01 00:00:00 | 因缺关键词排除 |
| `trash` | 已移入回收站 | 11-01 00:00:00 | 默认排除，`deleted=True` 时命中 |
| `empty` | 空正文 | 11-01 00:00:00 | 空关键词查询可用，无命中字段，空摘要 |
| `target` | 状态转移定义，供 UUID 链接验证 | 11-01 00:00:00 | 不命中该关键词查询，反链来自 body_hit |

默认演示查询为“动态规划 AI”＋“课程、ai”＋北京时间 11 月 1 日，预期 ID 顺序见 JSON 的 `active_hits`：`title_hit`、`body_hit`；回收站查询只返回 `trash`。D 可用该库接入界面后按上述清单逐项确认。

## 七、90 秒讲解稿（界面接入前用命令行替代）

- **0–15 秒**：说明当前后端已完成、界面待 D 接入。打开演示输出，展示查询“动态规划 AI”、课程+ai 标签及 11 月 1 日日期区间，条件一起取 AND。
- **15–35 秒**：对照起点前一微秒与终点笔记均被排除，解释起点包含、终点排除。结束日期次日零点保留当天最后一微秒，UTC 与北京时间只改变表示方式。
- **35–55 秒**：展示标题优先、真实命中位置及正文摘要。长文摘要中只看到“动态规划”，但完整正文还有“AI”，所以仍满足 AND；打开正文核对。
- **55–75 秒**：展示 UUID 目标和反向链接。打开 C3 中改名/删除恢复测试，说明代码/转义示例不会加入真实链接计数；这些是已有能力的回归验证。
- **75–90 秒**：打开 `search_hits` 和对应综合测试，说明复用 `search_notes` 保持返回和排序兼容，展示 63 项测试通过。明确界面操作及跨机验收仍待完成。

## 八、提交及未完成事项

- [C1：caac12d](https://github.com/zemengzero/MSGA/commit/caac12d53403d896f4a7ad72401a68bcf6c6f9d2)，日期过滤。
- [C2：1dce38e](https://github.com/zemengzero/MSGA/commit/1dce38ed5562e8305e1df77d5e5b64167016ef1e)，命中字段与摘要。
- [修正：b64cd0d](https://github.com/zemengzero/MSGA/commit/b64cd0d21da08f2b552294e378db63e51cca2afb)，UTC 日期溢出校验。
- [C3：ef9a962](https://github.com/zemengzero/MSGA/commit/ef9a96287fbb8c0fb3b8365cb15c4edc2dfaf2c9)，搜索/关联回归、演示工具及个人说明。完整历史见 [PR #14 提交列表](https://github.com/zemengzero/MSGA/pull/14/commits)。
- 姓名、学号已由本人提供并填写。Issue #7–#9 的认领及 D 对最新 main/PR #13 的集成安排，本轮未核验，交接时由本人和 D 确认。
- D 完成日期和摘要界面接入后再共同做真实界面验收；统一版本演练、另一台机器测试、真人反馈尚未完成。不要把后端通过测试写成这些环节已通过。

## 九、2026-11-02 复查补充

对照 C1–C3 与 C-T01–C-T09 复查，未发现新的日期筛选、关键词/标签 AND、排序、命中字段或摘要核心逻辑错误；已保留先前的 UTC 溢出修正。

本地补齐的交付遗漏：

- `docs/成员信息.csv` 的 C 行此前仍为空，现填写万语 / U202414607 / ZYQY218，并注明 PR 待审核及界面待接入；只修改 C 行。
- 本文补上 C3 的直接提交链接，C1/C2 交接说明更新“后续另行完成”的过时描述；原阶段测试日志保持不变。
- 新增 `docs/C_PR交接说明.md`，提供覆盖 C1–C3、日期转参、API 调用及限制的完整 PR 标题/正文草稿；没有更新远程 PR。
- 新增 `tests/test_c_demo.py` 的三个 CLI 回归测试：核对 9 篇合成笔记、实际 ID 顺序/命中字段/摘要/微秒边界/反链计数；确认已有文件不被覆盖；确认临时库清理。测试读取 SQLite 后显式关闭连接，避免 Windows 文件占用。

本轮实际执行 `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`，最终 **66 项全部通过**，2.030 秒，退出码 0，完整日志在 `reports/C_review_test_results.txt`。前文 63 项及 C3 演示结果是上次正式交付的阶段记录；最新本地复查以本节和新日志为准。

本次修改和新增验证材料随 `feature/c-search-links` 分支交付；PR 正文更新文案见 `C_PR交接说明.md`，该文件不会自动更新 GitHub 上的 PR 正文。Issue #7–#9 的指派属于远程协作操作，不可通过本地文件完成；本轮未修改 Issue。日期和摘要界面接入及整机验收依然待 D 完成，不计入已通过的本地测试。
