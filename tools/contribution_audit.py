"""Snapshot actual authors; planned roles are never counted as completed work."""

import csv
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
raw = subprocess.check_output(
    ["git", "log", "main", "--format=%H%x09%aN%x09%aE%x09%aI%x09%s"],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
)
commits = []
for line in raw.splitlines():
    sha, name, email, date, subject = line.split("\t", 4)
    commits.append(
        {
            "sha": sha,
            "author": name,
            "email": email,
            "authored_at": date,
            "subject": subject,
        }
    )
members = list(csv.DictReader((ROOT / "docs/成员信息.csv").open(encoding="utf-8-sig")))
rows = []
for member in members:
    login = member["GitHub账号"]
    matching = [
        c
        for c in commits
        if login != "待补充"
        and (
            c["author"] == login
            or c["email"]
            .lower()
            .endswith("+" + login.lower() + "@users.noreply.github.com")
        )
    ]
    rows.append(
        {
            "role": member["角色"],
            "name": member["姓名"],
            "github": login,
            "matching_actual_commits": len(matching),
            "status": "当前账号已有真实基线；个人增量仍按实际PR核验"
            if matching
            else "待本人账号和真实提交，未记为完成",
        }
    )
report = {
    "snapshot_head": commits[0]["sha"],
    "actual_commits": len(commits),
    "distinct_author_emails": len({c["email"] for c in commits}),
    "members": rows,
    "all_four_members_completed": False,
    "scope": "本地真实main记录快照；不把计划分摊给成员，远端身份可在GitHub核验",
}
(ROOT / "reports/contribution_status.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
with (ROOT / "reports/actual_commits.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as f:
    w = csv.DictWriter(f, fieldnames=list(commits[0]))
    w.writeheader()
    w.writerows(commits)
print(json.dumps(report, ensure_ascii=False))
