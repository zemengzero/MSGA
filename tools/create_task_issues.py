"""Create unassigned task cards; do not impersonate or mention teammates."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "IceApplejuice/zhiyeteam-software-engineering"
statefile = ROOT / ".git/team-issues.json"
state = json.loads(statefile.read_text(encoding="utf-8")) if statefile.exists() else {}
tasks = [
    (
        "A1",
        "A",
        "编辑器字号设置持久化",
        "ui.py + settings API；12–24字号，重开保持，正文不变。提交实现与验证。",
    ),
    (
        "A2",
        "A",
        "长文滚动与窄窗口布局",
        "完善正文/预览滚动条和焦点路径，截图只读本程序窗口。",
    ),
    (
        "A3",
        "A",
        "界面增量交互回归",
        "为A1/A2增加可执行交互测试及操作说明，保留失败证据。",
    ),
    (
        "B1",
        "B",
        "备份前空间预检",
        "在创建临时备份前估算空间，不能写时给明确错误，不改变当前库。",
    ),
    (
        "B2",
        "B",
        "恢复结果审计记录",
        "记录时间、备份/保护文件标识和成功/失败，不记录正文，审计不被恢复覆盖。",
    ),
    (
        "B3",
        "B",
        "备份空间与回退回归",
        "覆盖空间不足、审计失败、恢复/回退故障，按实际结果更新报告。",
    ),
    (
        "C1",
        "C",
        "可选更新时间过滤",
        "扩展search参数保持旧默认行为，时间边界明确，不改变AND/排序规则。",
    ),
    (
        "C2",
        "C",
        "检索命中摘要",
        "返回命中正文摘要与来源字段，纯函数可测试，与A协调界面入口。",
    ),
    (
        "C3",
        "C",
        "日期摘要及链接边界测试",
        "验证时间边界、空条件、中文子串、代码/转义和摘要长度，并更新代码导读。",
    ),
    (
        "D1",
        "D",
        "CI结构化证据工件",
        "让CI上传真实JSON/JUnit与失败日志，禁止固定填成功。",
    ),
    (
        "D2",
        "D",
        "发布门禁与第二台电脑验证",
        "测试/打包exe冒烟/SHA清单通过才发版，另用无Python电脑运行，记录实际环境。",
    ),
    (
        "D3",
        "D",
        "真实试用反馈与回归发布",
        "至少两名真实试用者；经同意记录反馈，修复真实问题/建议，加回归并更新报告。未发生不编造。",
    ),
]
for key, role, title, acceptance in tasks:
    if key in state:
        continue
    body = f"计划任务，尚未完成。负责人按组内角色 **{role}** 认领；真实姓名与GitHub账号待小组配置。\n\n## 实际工作与验收\n{acceptance}\n\n## 提交要求\n本人账号、功能分支、实质diff、测试记录、PR审核。建议消息围绕实际变更写，不用空提交或代签凑次数。\n\n完整计划：docs/团队分工与提交计划.md。"
    r = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{REPO}/issues", "--input", "-"],
        input=json.dumps(
            {"title": f"[{key}] {title}", "body": body}, ensure_ascii=False
        ),
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=40,
    )
    if r.returncode:
        raise RuntimeError(r.stderr)
    created = json.loads(r.stdout)
    state[key] = {
        "role": role,
        "title": title,
        "number": created["number"],
        "url": created["html_url"],
        "state": "open",
    }
    statefile.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
(ROOT / "reports/team_issue_plan.json").write_text(
    json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {"created_or_preserved": len(state), "all_unassigned_plan_items": True},
        ensure_ascii=False,
    )
)
