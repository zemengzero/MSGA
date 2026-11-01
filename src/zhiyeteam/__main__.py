import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="知页 · 本地学习知识库")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument(
        "--smoke-report", type=Path, default=Path("runtime/gui_smoke.json")
    )
    args = parser.parse_args()
    data_dir = args.data_dir or Path(
        os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")
    ) / "ZhiYeTeam" / ("demo" if args.demo else "personal")
    try:
        import tkinter as tk

        from .demo import seed_demo
        from .store import NoteStore
        from .ui import NotebookApp

        if sys.platform == "win32":
            import ctypes

            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except OSError:
                pass
        store = NoteStore(data_dir / "notes.db")
        if args.demo:
            seed_demo(store)
        root = tk.Tk()
        app = NotebookApp(root, store, data_dir, args.demo)
        if args.smoke_test:
            root.after(900, lambda: app.smoke(args.smoke_report))
        root.mainloop()
        if args.smoke_test:
            result = json.loads(args.smoke_report.read_text(encoding="utf-8"))
            return 0 if result.get("passed") else 1
        return 0
    except Exception as exc:
        if args.smoke_test:
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(
                json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            try:
                from tkinter import messagebox

                messagebox.showerror("知页启动未完成", str(exc))
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
