"""Collect installed upstream notices for the locally bundled UI/runtime."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runtime/galaxy-notices"
OUT.mkdir(parents=True, exist_ok=True)
items = []
for manifest in sorted((ROOT / "frontend/node_modules").glob("**/package.json")):
    # Nested source fixtures can have package.json but no meaningful name.
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        continue
    if not data.get("name") or not data.get("version"):
        continue
    files = [
        p
        for p in manifest.parent.iterdir()
        if p.is_file() and p.name.lower().startswith(("license", "copying", "notice"))
    ]
    if not files:
        continue
    label = data["name"].replace("/", "__").replace("@", "") + "-" + data["version"]
    target = OUT / "JavaScript" / label
    target.mkdir(parents=True, exist_ok=True)
    for p in files:
        (target / p.name).write_bytes(p.read_bytes())
    items.append(
        {
            "name": data["name"],
            "version": data["version"],
            "license": data.get("license"),
            "notices": [str(p.relative_to(OUT)) for p in target.iterdir()],
        }
    )
site = ROOT / ".venv/Lib/site-packages"
for directory in sorted(site.glob("*.dist-info")):
    if not directory.name.startswith(
        (
            "pywebview-",
            "pythonnet-",
            "clr_loader-",
            "cffi-",
            "bottle-",
            "proxy_tools-",
            "typing_extensions-",
            "markdown-",
            "pyinstaller-",
        )
    ):
        continue
    for p in directory.rglob("*"):
        if p.is_file() and p.name.lower().startswith(("license", "copying", "notice")):
            target = OUT / "Python" / directory.name / p.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(p.read_bytes())
python_license = Path(sys.base_prefix) / "LICENSE.txt"
(OUT / "Python-LICENSE.txt").write_bytes(python_license.read_bytes())
(OUT / "软件来源说明.txt").write_text(
    "知页知识星图：本组界面与业务适配代码。\n3D图谱使用react-force-graph-3d/Three.js；界面参考Blinko布局但未复制其GPL源码。\n本目录包含运行库及开发工具的原始许可文件，不表示所有开发工具都被打包进exe。\nWindows窗口使用系统已安装的Microsoft Edge WebView2 Runtime。\n",
    encoding="utf-8-sig",
)
(OUT / "JavaScript-packages.json").write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Collected upstream notices:", len(items), "JavaScript packages")
