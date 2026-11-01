"""Package actual artifacts and evidence, excluding personal databases and credentials."""

import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
VERSION = "v1.0.0"
REPO = "https://github.com/zemengzero/MSGA"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()


def load(name):
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def digest(content):
    return hashlib.sha256(content).hexdigest()


def main():
    RELEASE.mkdir(exist_ok=True)
    tests, frozen, build = [
        load(n) for n in ("test_results.json", "frozen_smoke.json", "build.json")
    ]
    assert (
        tests["passed"]
        and tests["failures"] == tests["errors"] == tests["skipped"] == 0
    )
    assert frozen["passed"] and frozen["self_contained_executable_launched"]
    assert all(x["word_pdf_content_matches"] for x in load("document_checks.json"))
    assert not git(
        "diff", "--name-only", tests["git_revision"], "--", "src", "tests"
    ), "Production/test source changed since measured tests; run checks and rebuild."
    assert not git(
        "status", "--porcelain", "--", "src", "tests", "tools", "docs", "README.md"
    ), "Commit reviewed source before packaging."
    exe = (ROOT / "dist/ZhiYeTeam.exe").read_bytes()
    assert digest(exe) == build["sha256"] and len(exe) == build["bytes"]
    head = git("rev-parse", "HEAD")
    audit = load("contribution_status.json")
    assert audit["snapshot_head"] == head, "Refresh contribution_audit.py first."
    publish = load("github_publish.json")
    assert publish["head"] == head and publish["all_original_commit_hashes_preserved"]
    ci = load("ci_status.json")
    assert ci["headSha"] == head and ci["conclusion"] == "success", (
        "Final CI has not passed."
    )
    source = RELEASE / "zhiyeteam-source.zip"
    subprocess.run(
        ["git", "archive", "--format=zip", "--output", str(source), head],
        cwd=ROOT,
        check=True,
    )
    bundle = RELEASE / "zhiyeteam-history.bundle"
    subprocess.run(
        ["git", "bundle", "create", str(bundle), "--all"], cwd=ROOT, check=True
    )
    subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    entries = {}

    def add(path, name):
        entries[name] = Path(path).read_bytes()

    entries["软件/ZhiYeTeam.exe"] = exe
    for label, arguments in (("启动演示", " --demo"), ("启动个人笔记", "")):
        entries[f"软件/{label}.bat"] = (
            '@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0ZhiYeTeam.exe"'
            + arguments
            + "\r\n"
        ).encode("ascii")
    for path in sorted((ROOT / "docs/generated").iterdir()):
        if path.suffix in (".pdf", ".docx"):
            add(path, "报告/" + path.name)
    assert sum(n.startswith("报告/") for n in entries) == 8
    add(source, "源码/" + source.name)
    add(bundle, "源码/" + bundle.name)
    for path in sorted((ROOT / "reports").iterdir()):
        if (
            path.suffix in (".json", ".csv", ".txt")
            and path.name != "release_manifest.json"
        ):
            add(path, "证据/" + path.name)
    for name in (
        "团队分工与提交计划.md",
        "现场演示步骤.md",
        "功能与代码定位.md",
        "成员信息.csv",
        "真实用户反馈记录.csv",
        "D_仓库统筹操作单.md",
    ):
        add(ROOT / "docs" / name, "分工与答辩/" + name)
    for name in ("architecture.png", "desktop.png"):
        add(ROOT / "docs/images" / name, "证据/截图/" + name)
    # Preserve licenses actually distributed by the installed runtime/build tools.
    licenses = {
        "Python-LICENSE.txt": Path(sys.base_prefix) / "LICENSE.txt",
        "Tk-license.terms": Path(sys.base_prefix) / "tcl/tk8.6/license.terms",
    }
    site = ROOT / ".venv/Lib/site-packages"
    for pattern, label in (
        ("markdown-*.dist-info/licenses/LICENSE.md", "Markdown-LICENSE.md"),
        ("pyinstaller-*.dist-info/licenses/COPYING.txt", "PyInstaller-COPYING.txt"),
    ):
        licenses[label] = next(site.glob(pattern))
    for name, path in licenses.items():
        add(path, "软件/第三方许可/" + name)
    entries["软件/第三方许可/说明.txt"] = (
        "独立程序包含Python/Tcl-Tk运行库、SQLite及Python-Markdown；"
        "使用PyInstaller打包。实际许可正文随本目录保留；"
        "Python许可文件包含所附第三方声明，PyInstaller文件包含bootloader例外。\n"
        "本项目源码未另行授予开源许可。\n"
    ).encode("utf-8-sig")
    entries["开始阅读.txt"] = (
        f"知页·本地学习知识库 {VERSION}\n\n"
        "1. 完整解压到电脑，打开“软件/启动演示.bat”，即可离线演示；无需安装Python。\n"
        "2. 打开“报告/01_团队项目实验报告.pdf”阅读选题、需求、设计和真实测试。"
        "同名Word供填写成员信息及后续修改；提交前检查姓名、学号和老师要求。\n"
        "3. 分工与答辩目录包含四人逐次提交计划、8分钟流程、功能代码定位。\n"
        "4. 默认个人数据在%LOCALAPPDATA%/ZhiYeTeam/personal；演示数据在同级demo，互不覆盖。\n"
        "5. 源码ZIP用于阅读，history.bundle保留真实历史；"
        "可执行 git clone zhiyeteam-history.bundle zhiyeteam-source 恢复仓库。\n"
        f"6. GitHub：{REPO}，当前公开；D负责协调全员协作权限、PR合并和发布。\n"
        f"源代码提交：{head}\n"
        f"本包实际单元/业务测试{tests['tests_run']}项通过，独立exe已在本机启动保存。"
        "第二台电脑验证与至少2名真人试用仍待小组实际执行，不能填成已完成。\n"
        f"当前main有{audit['actual_commits']}次真实提交，{audit['distinct_author_emails']}个作者邮箱；"
        "现有基线由当前账号AI辅助建立。其余成员要用本人账号完成有实质改动的任务，不能把计划当贡献。\n"
        "请填写另外三人的姓名/学号/GitHub账号，邀请协作者，认领任务；"
        "每人至少三次实质提交，保留diff、测试与PR，演示时讲本人代码。\n"
        "已确认2026-11-02验收，按今晚开发、课前冻结与演练安排。\n"
    ).encode("utf-8-sig")
    manifest = {
        "version": VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": head,
        "tested_production_revision": tests["git_revision"],
        "tests_passed": tests["tests_run"],
        "exe_sha256": build["sha256"],
        "ci_url": ci["url"],
        "repository": REPO,
        "repository_private": False,
        "files": [
            {"path": n, "bytes": len(b), "sha256": digest(b)}
            for n, b in sorted(entries.items())
        ],
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    entries["文件清单与SHA256.json"] = manifest_bytes
    (ROOT / "reports/release_manifest.json").write_bytes(manifest_bytes)
    output = RELEASE / f"ZhiYeTeam-MSGA-{VERSION}.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(entries.items()):
            z.writestr(name, content)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for row in manifest["files"]:
            assert digest(z.read(row["path"])) == row["sha256"]
    result = {
        "file": output.name,
        "bytes": output.stat().st_size,
        "sha256": digest(output.read_bytes()),
        "source_commit": head,
        "entries": len(entries),
        "zip_crc_and_sha_verified": True,
    }
    (RELEASE / "release_checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
