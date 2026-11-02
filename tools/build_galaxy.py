"""Build the React assets and a separate native Windows executable."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv/Scripts/python.exe"
subprocess.run(["npm.cmd", "run", "build"], cwd=ROOT / "frontend", check=True)
args = [
    str(PYTHON),
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name",
    "ZhiYeGalaxy",
    "--paths",
    str(ROOT / "src"),
    "--add-data",
    str(ROOT / "src/zhiyeteam/schema.sql") + ";zhiyeteam",
    "--add-data",
    str(ROOT / "frontend/dist") + ";zhiyeteam/web",
    "--icon",
    str(ROOT / "src/zhiyeteam/assets/icon.ico"),
    "--collect-all",
    "webview",
    "--collect-all",
    "pythonnet",
    "--collect-all",
    "clr_loader",
    "--collect-all",
    "markdown",
    "--exclude-module",
    "PyQt5",
    "--exclude-module",
    "PyQt6",
    "--exclude-module",
    "PySide2",
    "--exclude-module",
    "PySide6",
    str(ROOT / "tools/launch_galaxy.py"),
]
for module in ("restore_audit", "search_presenter"):
    if (ROOT / "src/zhiyeteam" / (module + ".py")).is_file():
        args[-1:-1] = ["--hidden-import", "zhiyeteam." + module]
subprocess.run(args, cwd=ROOT, check=True)
exe = ROOT / "dist/ZhiYeGalaxy.exe"
data = {
    "file": exe.name,
    "bytes": exe.stat().st_size,
    "sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
    "source_revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "web_index_sha256": hashlib.sha256(
        (ROOT / "frontend/dist/index.html").read_bytes()
    ).hexdigest(),
    "runtime": "Windows x64 + installed Edge WebView2 Runtime",
    "offline_assets_bundled": True,
    "source_files_sha256": {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            *sorted((ROOT / "src/zhiyeteam").glob("*.py")),
            ROOT / "src/zhiyeteam/schema.sql",
            ROOT / "frontend/package-lock.json",
            *sorted((ROOT / "frontend/src").glob("*")),
        ]
        if p.is_file()
    },
}
(ROOT / "reports/A/galaxy-build.json").write_text(
    json.dumps(data, indent=2), encoding="utf-8"
)
print(json.dumps(data))
