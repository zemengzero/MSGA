"""Transport actual local Git history through GitHub Git Data API.

Used when github.com Git transport is blocked but api.github.com is reachable.
Author/committer names, emails, actual dates, messages and trees are copied from
existing local objects. This does not generate teammate identities or backdate work.
"""

import base64
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "IceApplejuice/zhiyeteam-software-engineering"
PREFIX = "repos/" + REPO
STATE = ROOT / ".git/api-publish-state.json"
state = (
    json.loads(STATE.read_text(encoding="utf-8"))
    if STATE.exists()
    else {"blobs": [], "commits": {}}
)
lock = threading.Lock()


def save_state():
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def api(method, path, payload=None, missing=False):
    cmd = ["gh", "api", "--method", method, path]
    if payload is not None:
        cmd += ["--input", "-"]
    for attempt in range(3):
        r = subprocess.run(
            cmd,
            input=json.dumps(payload, ensure_ascii=False)
            if payload is not None
            else None,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
        )
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout.strip() else None
        if missing and ("404" in r.stderr or "409" in r.stderr):
            return None
        if attempt < 2:
            time.sleep(1)
    raise RuntimeError(method + " " + path + ": " + r.stderr[-500:])


def identity(raw):
    m = re.fullmatch(r"(.+) <([^>]+)> (\d+) ([+-]\d{4})", raw)
    if not m:
        raise RuntimeError("不支持的提交元数据，停止上传")
    zone = m[4]
    minutes = (int(zone[1:3]) * 60 + int(zone[3:])) * (1 if zone[0] == "+" else -1)
    date = datetime.fromtimestamp(
        int(m[3]), timezone(timedelta(minutes=minutes))
    ).isoformat()
    return {"name": m[1], "email": m[2], "date": date}


def entries(commit):
    result = []
    for record in git("ls-tree", "-r", "-z", commit).split(b"\0"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, sha = header.decode().split()
        if kind != "blob":
            raise RuntimeError("本传输工具不处理子模块")
        result.append(
            {"path": name.decode("utf-8"), "mode": mode, "type": "blob", "sha": sha}
        )
    return result


def upload_blob(sha):
    result = api(
        "POST",
        PREFIX + "/git/blobs",
        {
            "encoding": "base64",
            "content": base64.b64encode(git("cat-file", "blob", sha)).decode("ascii"),
        },
    )
    if result["sha"] != sha:
        raise RuntimeError("文件对象哈希不一致")
    with lock:
        state["blobs"].append(sha)
        save_state()


def main():
    head = api("GET", PREFIX + "/git/ref/heads/main", missing=True)
    if not head:
        init = api(
            "PUT",
            PREFIX + "/contents/.offline-transfer-bootstrap",
            {
                "message": "chore: initialize transport for existing offline development history",
                "content": base64.b64encode(
                    b"Temporary transport bootstrap; the main branch will be the original development history.\n"
                ).decode(),
            },
        )
        state["bootstrap"] = init["commit"]["sha"]
        save_state()
        head = api("GET", PREFIX + "/git/ref/heads/main")
    actual_head = head["object"]["sha"]
    allowed = {state.get("bootstrap"), state.get("published_head")}
    if actual_head not in allowed:
        raise RuntimeError("远端出现未由本工具创建的新提交，停止以保护他人改动")
    if state.get("bootstrap") and not api(
        "GET", PREFIX + "/git/ref/heads/transport-bootstrap", missing=True
    ):
        api(
            "POST",
            PREFIX + "/git/refs",
            {"ref": "refs/heads/transport-bootstrap", "sha": state["bootstrap"]},
        )
    commits = git("rev-list", "--reverse", "main").decode().splitlines()
    all_entries = {c: entries(c) for c in commits}
    blobs = {e["sha"] for es in all_entries.values() for e in es} - set(state["blobs"])
    print("Uploading real file objects:", len(blobs), flush=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [executor.submit(upload_blob, b) for b in blobs]
        for n, f in enumerate(as_completed(jobs), 1):
            f.result()
            if n % 20 == 0:
                print("Uploaded objects", n, flush=True)
    for c in commits:
        if c in state["commits"]:
            continue
        raw = git("cat-file", "commit", c).decode("utf-8")
        headers, message = raw.split("\n\n", 1)
        parsed = {}
        parents = []
        for line in headers.splitlines():
            key, _, value = line.partition(" ")
            if key == "parent":
                parents.append(value)
            elif key in ["tree", "author", "committer"]:
                parsed[key] = value
        tree = api("POST", PREFIX + "/git/trees", {"tree": all_entries[c]})
        if tree["sha"] != parsed["tree"]:
            raise RuntimeError("目录树哈希不一致，未更新远端分支")
        payload = {
            "tree": tree["sha"],
            "message": message,
            "parents": [state["commits"].get(p, p) for p in parents],
            "author": identity(parsed["author"]),
            "committer": identity(parsed["committer"]),
        }
        remote = api("POST", PREFIX + "/git/commits", payload)
        state["commits"][c] = remote["sha"]
        save_state()
        print(
            "Uploaded actual commit",
            c[:8],
            "->",
            remote["sha"][:8],
            message.splitlines()[0],
            flush=True,
        )
    last = state["commits"][commits[-1]]
    current = api("GET", PREFIX + "/git/ref/heads/main")["object"]["sha"]
    if current != actual_head:
        raise RuntimeError("上传期间远端被更改，未覆盖")
    api(
        "PATCH",
        PREFIX + "/git/refs/heads/main",
        {"sha": last, "force": current == state.get("bootstrap")},
    )
    state["published_head"] = last
    save_state()
    report = {
        "repository": "https://github.com/" + REPO,
        "private": True,
        "method": "Git Data API transport of existing local history",
        "source_commits": len(commits),
        "all_original_commit_hashes_preserved": all(
            c == state["commits"][c] for c in commits
        ),
        "local_to_remote": {c: state["commits"][c] for c in commits},
        "head": last,
        "authors_and_dates_copied_from_actual_local_commits": True,
    }
    (ROOT / "reports/github_publish.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "local_to_remote"},
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
