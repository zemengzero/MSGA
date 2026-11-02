"""Exercise A's changes using actual Tk widgets and isolated synthetic notes."""

import ctypes
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tkinter import Tk, font

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from zhiyeteam.store import NoteStore
from zhiyeteam.ui import NotebookApp
from window_capture import capture_owned_window


def run():
    if sys.platform == "win32":
        ctypes.windll.user32.SetProcessDPIAware()
    output = ROOT / "reports/A"
    output.mkdir(parents=True, exist_ok=True)
    data = ROOT / "runtime" / ("a-ui-" + uuid.uuid4().hex[:10])
    store = NoteStore(data / "notes.db")
    body = "# A界面交互验证\n\n" + "\n\n".join(
        f"第{i}段：滚动与布局测试。" for i in range(400)
    )
    note = store.create("A合成验收笔记", body, [f"标签{i}" for i in range(12)])
    root = Tk()
    try:
        app = NotebookApp(root, store, data, True)
        app.open_note(note.id, True)
        root.update()
        checks = {}
        app.font_size_var.set("18")
        app.font_picker.event_generate("<<ComboboxSelected>>")
        root.update()
        checks["actual_combobox_saves_font"] = (
            store.settings("editor_font_size") == 18
            and font.Font(root=root, font=app.editor.cget("font")).actual("size") == 18
        )
        checks["font_does_not_edit_note"] = store.get(note.id) == note and not app.dirty
        checks["sidebar_more_than_eight_tags"] = (
            len(app.tag_frame.winfo_children()) == 12
        )
        for label, widget, scrollbar in (
            ("editor", app.editor, app.editor_scrollbar),
            ("preview", app.preview, app.preview_scrollbar),
        ):
            widget.yview_moveto(1.0)
            root.update()
            checks[label + "_long_content_scrolls"] = widget.yview()[0] > 0 and bool(
                scrollbar.winfo_ismapped()
            )
        root.geometry("980x720")
        root.update()
        checks["narrow_window_hides_preview"] = (
            not app.preview_visible and len(app.paned.panes()) == 2
        )
        checks["narrow_window_keeps_save_and_tags_visible"] = (
            app.save_button.winfo_viewable()
            and app.tags_entry.winfo_viewable()
            and app.save_button.winfo_rootx() + app.save_button.winfo_width()
            <= root.winfo_rootx() + root.winfo_width()
        )
        checks["resize_keeps_editor_content"] = app.editor.get("1.0", "end-1c") == body
        if sys.platform == "win32":
            capture_owned_window(root, output / "narrow.png")
        root.geometry("1480x900")
        root.update()
        checks["wide_window_restores_preview"] = (
            app.preview_visible and len(app.paned.panes()) == 3
        )
        if sys.platform == "win32":
            capture_owned_window(root, output / "wide.png")
        if app.smoke_error:
            raise AssertionError(app.smoke_error)
    finally:
        root.destroy()
        store.close()
    store = NoteStore(data / "notes.db")
    root = Tk()
    try:
        app = NotebookApp(root, store, data, True)
        root.update()
        checks["reopened_app_restores_font"] = app.editor_font_size == 18
    finally:
        root.destroy()
        store.close()
    result = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "actual Tk controls; isolated synthetic data; not user feedback",
        "ui_source_sha256": hashlib.sha256(
            (ROOT / "src/zhiyeteam/ui.py").read_bytes()
        ).hexdigest(),
        "checks": {k: bool(v) for k, v in checks.items()},
        "passed": all(checks.values()),
    }
    (output / "ui_checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    assert result["passed"], "A实际界面检查失败"


if __name__ == "__main__":
    run()
