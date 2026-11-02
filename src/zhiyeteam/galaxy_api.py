"""Thread-safe UI adapter. Existing domain modules remain the source of truth."""

import html
import importlib
import inspect
import re
import threading
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .backup import create_backup, inspect_backup, restore_backup
from .galaxy_demo import seed_galaxy_demo
from .links import backlinks, extract_links
from .models import AppError, ValidationError
from .search import search_notes, tag_counts
from .store import NoteStore
from .transfer import export_notes, import_markdown, safe_markdown_html

PALETTE = ["#a78bfa", "#67b8fa", "#f29cc8", "#64d7be", "#f6c176", "#8d9ef5", "#bfc5d8"]


def optional_function(module, name):
    full_name = __package__ + "." + module
    try:
        value = importlib.import_module(full_name)
    except ModuleNotFoundError as exc:
        if exc.name == full_name:
            return None
        raise
    fn = getattr(value, name, None)
    return fn if callable(fn) else None


class GalaxyAPI:
    ACTIONS = {
        "snapshot",
        "note",
        "create",
        "save",
        "trash",
        "purge",
        "history",
        "restore_version",
        "preferences",
        "pin",
        "backup",
        "pick_restore",
        "restore",
        "export",
        "import",
    }

    def __init__(self, data_dir, demo=False):
        self.data_dir = Path(data_dir).resolve()
        self.path = self.data_dir / "notes.db"
        self.demo = demo
        self.window = None
        self.lock = threading.RLock()
        self.write_locked = False
        self.restore_choices = {}
        with self.lock:
            store = NoteStore(self.path)
            try:
                if demo:
                    seed_galaxy_demo(store)
            finally:
                store.close()

    def invoke(self, action, payload=None):
        if action not in self.ACTIONS:
            return {"ok": False, "error": "不支持的操作", "type": "ValidationError"}
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "请求格式不正确", "type": "ValidationError"}
        # A connection is created and used on the same HTTP worker thread.
        with self.lock:
            store = None
            try:
                store = NoteStore(self.path)
                store.writes_disabled = self.write_locked
                result = self._dispatch(store, action, payload)
                return {"ok": True, "data": result}
            except Exception as exc:
                return {
                    "ok": False,
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "write_locked": self.write_locked
                    or bool(store and store.writes_disabled),
                }
            finally:
                if store:
                    self.write_locked = self.write_locked or store.writes_disabled
                    store.close()

    def _snapshot(self, store, payload):
        active = store.list_notes()
        visible = active[:150]
        ids = {n.id for n in visible}
        rows = store.conn.execute(
            "SELECT l.source_id,l.target_id,l.occurrences FROM links l JOIN notes s ON s.id=l.source_id JOIN notes t ON t.id=l.target_id WHERE s.deleted=0 AND t.deleted=0"
        ).fetchall()
        degree = {n.id: 0 for n in visible}
        edges = []
        for source, target, count in rows:
            if source in ids and target in ids:
                edges.append({"source": source, "target": target, "weight": count})
                degree[source] += 1
                if source != target:
                    degree[target] += 1
        tags = tag_counts(store)
        colors = {tag: PALETTE[i % len(PALETTE)] for i, (tag, _) in enumerate(tags)}
        pinned = store.settings("pinned_ids", [])

        def summary(n):
            return {k: v for k, v in asdict(n).items() if k != "body"} | {
                "excerpt": re.sub(
                    r"\s+", " ", re.sub(r"\[\[note:[^\]]+\]\]", "", n.body)
                ).strip()[:160],
                "pinned": n.id in pinned,
                "color": colors.get(n.tags[0] if n.tags else "", PALETTE[0]),
            }

        date_support = {"updated_from", "updated_before"}.issubset(
            inspect.signature(search_notes).parameters
        )
        hit_search = optional_function("search", "search_hits") or optional_function(
            "search_presenter", "search_hits"
        )
        audit = optional_function("restore_audit", "restore_with_audit")
        kwargs = {}
        if payload.get("date_from") or payload.get("date_to"):
            if not date_support:
                raise ValidationError(
                    "日期筛选需要合并C成员的搜索扩展；当前基础搜索仍可使用"
                )
            zone = timezone(timedelta(hours=8))
            for key, parameter in (
                ("date_from", "updated_from"),
                ("date_to", "updated_before"),
            ):
                value = payload.get(key)
                if value:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise ValidationError("请选择有效日期")
                    try:
                        parsed = datetime.strptime(value, "%Y-%m-%d").replace(
                            tzinfo=zone
                        )
                    except ValueError as exc:
                        raise ValidationError("请选择有效日期") from exc
                    kwargs[parameter] = (
                        parsed + timedelta(days=1) if key == "date_to" else parsed
                    )
        args = (
            store,
            payload.get("query", ""),
            payload.get("tags", []),
            bool(payload.get("deleted", False)),
        )
        matches = search_notes(*args, **kwargs)
        snippets = {}
        if hit_search:
            for hit in hit_search(*args, **kwargs):
                note = hit["note"] if isinstance(hit, dict) else hit.note
                snippet = (
                    hit.get("snippet", "") if isinstance(hit, dict) else hit.snippet
                )
                fields = (
                    hit.get("matched_fields", ())
                    if isinstance(hit, dict)
                    else hit.matched_fields
                )
                snippets[note.id] = {
                    "excerpt": str(snippet),
                    "matched_fields": list(fields),
                }
        font_size = store.settings("editor_font_size", 14)
        return {
            "stats": store.stats() | {"connections": len(rows)},
            "notes": [summary(n) | snippets.get(n.id, {}) for n in matches[:200]],
            "match_count": len(matches),
            "matched_ids": [n.id for n in matches],
            "tags": [{"name": t, "count": c, "color": colors[t]} for t, c in tags],
            "graph": {
                "nodes": [summary(n) | {"degree": degree[n.id]} for n in visible],
                "links": edges,
            },
            "graph_limit": 150,
            "demo": self.demo,
            "font_size": font_size
            if type(font_size) is int and 12 <= font_size <= 24
            else 14,
            "pinned_ids": pinned,
            "write_locked": self.write_locked,
            "capabilities": {
                "date_filters": date_support,
                "hit_snippets": bool(hit_search),
                "restore_audit": bool(audit),
            },
        }

    def _note(self, store, note_id):
        note = store.get(note_id)
        body = note.body
        for link in reversed(extract_links(body)):
            try:
                target = store.get(link.target)
                label = link.alias or target.title
                replacement = (
                    f"[{html.escape(label).replace('[', '').replace(']', '')}](#note:{target.id})"
                    if not target.deleted
                    else "关联笔记在回收站"
                )
            except ValidationError:
                replacement = "关联笔记不可用"
            body = body[: link.start] + replacement + body[link.end :]
        return asdict(note) | {
            "html": safe_markdown_html(body),
            "backlinks": [
                {"id": n.id, "title": n.title, "count": c}
                for n, c in backlinks(store, note.id)
            ],
        }

    def _dialog(self, kind, **kwargs):
        if self.window is None:
            raise ValidationError("请在桌面程序中使用文件选择功能")
        import webview

        return self.window.create_file_dialog(
            getattr(webview.FileDialog, kind), **kwargs
        )

    def _dispatch(self, store, action, p):
        if action == "snapshot":
            return self._snapshot(store, p)
        if action == "note":
            return self._note(store, p["id"])
        if action == "create":
            return asdict(
                store.create(
                    p.get("title", "未命名的灵感"), p.get("body", ""), p.get("tags", [])
                )
            )
        if action == "save":
            # The revision is required for every edit made through this UI.
            if type(p.get("revision")) is not int:
                raise ValidationError("保存需要有效的笔记版本")
            return asdict(
                store.save(
                    p["id"], p["title"], p["body"], p.get("tags", []), p["revision"]
                )
            )
        if action == "trash":
            return asdict(store.set_deleted(p["id"], bool(p["deleted"])))
        if action == "purge":
            store.purge(p["id"])
            return {"purged": True}
        if action == "history":
            return store.versions(p["id"])
        if action == "restore_version":
            if type(p.get("revision")) is not int:
                raise ValidationError("回退需要当前版本")
            return asdict(
                store.restore_version(p["id"], p["history_id"], p["revision"])
            )
        if action == "preferences":
            value = p["font_size"]
            if type(value) is not int or not 12 <= value <= 24:
                raise ValidationError("字号必须为12–24之间的整数")
            store.set_setting("editor_font_size", value)
            return {"font_size": value}
        if action == "pin":
            store.get(p["id"])
            pinned = set(store.settings("pinned_ids", []))
            pinned.remove(p["id"]) if p["id"] in pinned else pinned.add(p["id"])
            store.set_setting("pinned_ids", sorted(pinned))
            return {"pinned_ids": sorted(pinned)}
        if action == "backup":
            selected = self._dialog(
                "SAVE",
                save_filename="知页备份_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
                + ".db",
                file_types=("知页备份 (*.db)",),
            )
            if not selected:
                return {"cancelled": True}
            path = selected if isinstance(selected, str) else selected[0]
            return {"path": str(create_backup(store, path))}
        if action == "pick_restore":
            selected = self._dialog("OPEN", file_types=("知页备份 (*.db)",))
            if not selected:
                return {"cancelled": True}
            path = selected if isinstance(selected, str) else selected[0]
            info = inspect_backup(path)
            token = uuid.uuid4().hex
            self.restore_choices = {token: path}
            return info | {"token": token, "name": Path(path).name}
        if action == "restore":
            path = self.restore_choices.pop(p.get("token", ""), None)
            if path is None:
                raise ValidationError("请重新选择并确认备份")
            audited = optional_function("restore_audit", "restore_with_audit")
            if audited:
                report = audited(
                    store,
                    path,
                    self.data_dir / "backups",
                    self.data_dir / "audit/restore.jsonl",
                )
                protected = (
                    report["protection_path"]
                    if isinstance(report, dict)
                    else report.protection_path
                )
                warning = (
                    report.get("audit_warning")
                    if isinstance(report, dict)
                    else report.audit_warning
                )
                return {"protection_path": str(protected), "audit_warning": warning}
            protected = restore_backup(store, path, self.data_dir / "backups")
            return {"protection_path": str(protected), "audit_warning": None}
        if action == "export":
            selected = self._dialog("FOLDER")
            if not selected:
                return {"cancelled": True}
            path = selected if isinstance(selected, str) else selected[0]
            return {
                "count": len(export_notes(store, path, p.get("kind", "html"))),
                "path": path,
            }
        if action == "import":
            selected = self._dialog(
                "OPEN", allow_multiple=True, file_types=("Markdown (*.md)",)
            )
            if not selected:
                return {"cancelled": True}
            paths = [selected] if isinstance(selected, str) else selected
            return {"items": import_markdown(store, paths)}
