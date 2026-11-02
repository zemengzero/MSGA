"""Native Windows WebView shell for the locally bundled React knowledge graph."""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

from .galaxy_api import GalaxyAPI
from .galaxy_server import serve


def close_guard(window):
    """Do not synchronously query WebView from its blocking FormClosing event."""
    state = {"busy": False, "approved": False}

    def decide():
        try:
            try:
                dirty = window.evaluate_js("Boolean(window.__hasUnsavedChanges)")
                message = (
                    "仍有未保存内容。确定退出将丢弃这些修改；取消可返回编辑并保存。"
                    if dirty
                    else None
                )
            except Exception:
                message = "暂时无法确认编辑状态。请确认已保存需要的内容，仍要退出吗？"
            if message and not window.create_confirmation_dialog("退出确认", message):
                return
            state["approved"] = True
            window.destroy()
        finally:
            state["busy"] = False

    def on_closing():
        if state["approved"]:
            return True
        if not state["busy"]:
            state["busy"] = True
            threading.Thread(target=decide, daemon=True).start()
        return False

    return on_closing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--server-info", type=Path)
    parser.add_argument("--smoke-report", type=Path)
    args = parser.parse_args()
    data = args.data_dir or Path(
        os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")
    ) / "ZhiYeTeam" / ("galaxy-demo" if args.demo else "personal")
    assets = Path(__file__).with_name("web")
    if not assets.is_dir():
        assets = Path(__file__).resolve().parents[2] / "frontend/dist"
    if not (assets / "index.html").is_file():
        raise SystemExit("请先在frontend目录执行npm run build")
    api = GalaxyAPI(data, args.demo)
    server, url = serve(api, assets)
    try:
        if args.server_info:
            args.server_info.parent.mkdir(parents=True, exist_ok=True)
            args.server_info.write_text(
                json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8"
            )
        if args.server:
            while True:
                time.sleep(1)
        import webview

        window = webview.create_window(
            "知页 · 知识星图",
            url,
            width=1460,
            height=940,
            min_size=(1000, 680),
            background_color="#0c0d15",
            text_select=True,
        )
        api.window = window

        window.events.closing += close_guard(window)

        def smoke():
            if not args.smoke_report:
                return
            result = {"passed": False}
            try:
                for _ in range(100):
                    time.sleep(0.2)
                    if window.evaluate_js("Boolean(window.__appReady)"):
                        break
                else:
                    raise RuntimeError("前端未就绪")
                window.evaluate_js("window.__desktopSmoke(); true")
                for _ in range(100):
                    time.sleep(0.2)
                    result = window.evaluate_js("window.__desktopSmokeResult || null")
                    if result is not None:
                        break
                else:
                    raise RuntimeError("桌面保存检查超时")
                result["native_window"] = True
            except Exception as exc:
                result = {"passed": False, "error": str(exc)}
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            window.destroy()

        webview.start(smoke, gui="edgechromium", debug=False)
        if args.smoke_report:
            return (
                0
                if json.loads(args.smoke_report.read_text(encoding="utf-8")).get(
                    "passed"
                )
                else 1
            )
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
