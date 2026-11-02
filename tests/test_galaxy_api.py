import json
import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from support import StoreFixture
from zhiyeteam.backup import create_backup
from zhiyeteam.galaxy_api import GalaxyAPI
from zhiyeteam.models import AppError
from zhiyeteam.search import search_notes


class GalaxyTests(StoreFixture):
    def setUp(self):
        super().setUp()
        self.api = GalaxyAPI(self.path.parent)

    def call(self, action, payload=None):
        response = self.api.invoke(action, payload)
        self.assertTrue(response["ok"], response)
        return response["data"]

    def test_graph_uses_actual_links_and_excludes_trash_and_dangling(self):
        a = self.store.create("原笔记")
        b = self.store.create("目标")
        c = self.store.create(
            "来源", f"[[note:{a.id}]] [[note:{a.id}]] [[note:{b.id}]]"
        )
        self.store.set_deleted(b.id, True)
        state = self.call("snapshot")
        self.assertEqual({n["id"] for n in state["graph"]["nodes"]}, {a.id, c.id})
        self.assertEqual(
            state["graph"]["links"], [{"source": c.id, "target": a.id, "weight": 2}]
        )
        self.assertEqual(state["stats"]["connections"], 1)
        self.store.set_deleted(b.id, False)
        self.assertEqual(len(self.call("snapshot")["graph"]["links"]), 2)

    def test_safe_preview_resolves_renamed_link_without_script(self):
        a = self.store.create("目标")
        b = self.store.create(
            "来源",
            f"[[note:{a.id}]] <img src=x onerror=alert(1)><script>alert(1)</script>",
        )
        self.store.save(a.id, "已改名", "", (), a.revision)
        rendered = self.call("note", {"id": b.id})["html"]
        self.assertIn("已改名", rendered)
        self.assertIn("#note:" + a.id, rendered)
        self.assertNotIn("<script", rendered)
        self.assertNotIn("onerror", rendered)

    def test_api_requires_revision_and_preserves_stale_buffer(self):
        note = self.call("create", {"title": "A", "body": "old"})
        saved = self.call("save", note | {"body": "new"})
        stale = self.api.invoke("save", note | {"body": "stale"})
        self.assertFalse(stale["ok"])
        self.assertEqual(stale["type"], "ConflictError")
        self.assertEqual(self.store.get(note["id"]).body, "new")
        self.assertFalse(self.api.invoke("save", saved | {"revision": None})["ok"])

    def test_font_and_pin_do_not_change_note_revision(self):
        note = self.store.create("A", "same")
        self.call("preferences", {"font_size": 18})
        self.call("pin", {"id": note.id})
        state = self.call("snapshot")
        self.assertEqual(state["font_size"], 18)
        self.assertIn(note.id, state["pinned_ids"])
        self.assertEqual(self.store.get(note.id), note)
        self.assertFalse(self.api.invoke("preferences", {"font_size": True})["ok"])

    def test_calls_work_from_different_worker_threads(self):
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(
                pool.map(
                    lambda i: self.api.invoke("create", {"title": f"笔记{i}"}),
                    range(10),
                )
            )
        self.assertTrue(all(r["ok"] for r in responses))
        self.assertEqual(self.store.stats()["active"], 10)

    def test_graph_does_not_seed_existing_library(self):
        self.store.create("真实内容", "不要覆盖")
        another = GalaxyAPI(self.path.parent, demo=True)
        self.assertEqual(another.invoke("snapshot")["data"]["stats"]["active"], 1)

    def test_backup_restore_and_export_reuse_existing_modules(self):
        note = self.store.create("A", "old")
        backup = self.path.parent / "backup.db"
        with patch.object(self.api, "_dialog", return_value=str(backup)):
            self.call("backup")
        self.store.save(note.id, "A", "new", (), note.revision)
        with patch.object(self.api, "_dialog", return_value=[str(backup)]):
            choice = self.call("pick_restore")
        result = self.call("restore", {"token": choice["token"]})
        self.assertTrue(result["protection_path"].endswith(".db"))
        self.assertEqual(self.store.get(note.id).body, "old")
        self.assertFalse(self.api.invoke("restore", {"token": choice["token"]})["ok"])
        directory = self.path.parent / "export"
        with patch.object(self.api, "_dialog", return_value=[str(directory)]):
            self.call("export", {"kind": "html"})
        self.assertTrue((directory / "index.html").is_file())

    def test_failed_restore_keeps_protection_lock_across_requests(self):
        self.store.create("A")
        snapshot = self.path.parent / "backup.db"
        create_backup(self.store, snapshot)
        self.api.restore_choices["selected"] = str(snapshot)

        def fail(store, *_):
            store.writes_disabled = True
            raise AppError("恢复与回退失败")

        with patch("zhiyeteam.galaxy_api.restore_backup", side_effect=fail):
            self.assertFalse(self.api.invoke("restore", {"token": "selected"})["ok"])
        self.assertTrue(self.call("snapshot")["write_locked"])
        self.assertFalse(self.api.invoke("create", {"title": "blocked"})["ok"])

    def test_C_date_contract_is_aware_and_end_date_inclusive(self):
        note = self.store.create("C")
        observed = {}

        def dated(
            store,
            keywords="",
            tags=(),
            deleted=False,
            *,
            updated_from=None,
            updated_before=None,
        ):
            observed.update(start=updated_from, end=updated_before)
            return search_notes(store, keywords, tags, deleted)

        with patch("zhiyeteam.galaxy_api.search_notes", dated):
            state = self.call(
                "snapshot", {"date_from": "2026-11-01", "date_to": "2026-11-01"}
            )
        self.assertTrue(state["capabilities"]["date_filters"])
        self.assertEqual(
            observed["start"].astimezone(timezone.utc),
            datetime(2026, 10, 31, 16, tzinfo=timezone.utc),
        )
        self.assertEqual(
            observed["end"].astimezone(timezone.utc),
            datetime(2026, 11, 1, 16, tzinfo=timezone.utc),
        )

    def test_C_search_hit_contract_supports_separate_presenter(self):
        note = self.store.create("C", "original")
        module = ModuleType("zhiyeteam.search_presenter")
        module.search_hits = lambda *a, **k: [
            SimpleNamespace(note=note, snippet="C生成的摘要", matched_fields=("body",))
        ]
        with patch.dict(sys.modules, {module.__name__: module}):
            state = self.call("snapshot")
        self.assertEqual(state["notes"][0]["excerpt"], "C生成的摘要")
        self.assertEqual(state["notes"][0]["matched_fields"], ["body"])

    def test_B_audit_wrapper_contract_does_not_change_legacy_restore(self):
        module = ModuleType("zhiyeteam.restore_audit")
        seen = []

        def audited(store, source, protection_dir, audit_path):
            seen.append(audit_path)
            return SimpleNamespace(
                protection_path=protection_dir / "protected.db",
                audit_warning="审计未写入",
            )

        module.restore_with_audit = audited
        self.api.restore_choices["selection"] = "selected-source.db"
        with patch.dict(sys.modules, {module.__name__: module}):
            result = self.call("restore", {"token": "selection"})
        self.assertEqual(result["audit_warning"], "审计未写入")
        self.assertEqual(seen[0], self.path.parent / "audit/restore.jsonl")

    def test_unimplemented_optional_filters_fail_explicitly(self):
        result = self.api.invoke("snapshot", {"date_from": "2026-11-01"})
        self.assertFalse(result["ok"])
        self.assertIn("日期", result["error"])
        self.assertFalse(self.api.invoke("unknown", {})["ok"])
