import json
import types
from pathlib import Path
from unittest.mock import patch

from support import StoreFixture

from zhiyeteam import backup
from zhiyeteam.backup import create_backup, inspect_backup, restore_backup
from zhiyeteam.models import AppError, ValidationError
from zhiyeteam.restore_audit import AUDIT_WARNING, restore_with_audit


class BackupPolicyTests(StoreFixture):
    def _make_backup(self, name="snapshot.db"):
        target = self.path.parent / name
        with patch(
            "zhiyeteam.backup.shutil.disk_usage",
            return_value=types.SimpleNamespace(free=10**12),
        ):
            create_backup(self.store, target)
        return target

    def _audit_path(self):
        return self.path.parent / "audit" / "restore.jsonl"

    def _records(self, path):
        return [
            json.loads(line)
            for line in Path(path).read_text(encoding="utf-8").splitlines()
        ]

    def test_b01_sufficient_space_creates_valid_backup_without_changing_store(self):
        note = self.store.create("A", "original")
        target = self.path.parent / "snapshot.db"
        with patch(
            "zhiyeteam.backup.shutil.disk_usage",
            return_value=types.SimpleNamespace(free=10**12),
        ):
            create_backup(self.store, target)

        self.assertEqual(inspect_backup(target)["notes"], 1)
        self.assertEqual(self.store.get(note.id).body, "original")
        self.assertEqual(self.store.get(note.id).revision, 1)

    def test_b02_insufficient_space_refuses_before_creating_target_or_partial(self):
        note = self.store.create("A", "keep")
        target = self.path.parent / "missing" / "deep" / "snapshot.db"

        with patch(
            "zhiyeteam.backup.shutil.disk_usage",
            return_value=types.SimpleNamespace(free=1),
        ):
            with self.assertRaises(ValidationError) as caught:
                create_backup(self.store, target)

        self.assertIn("空间不足", str(caught.exception))
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())
        self.assertFalse(list(self.path.parent.rglob("*.partial-*")))
        current = self.store.get(note.id)
        self.assertEqual((current.body, current.revision), ("keep", 1))

    def test_b03_nested_target_uses_nearest_existing_parent_volume(self):
        target = self.path.parent / "new" / "deep" / "snapshot.db"
        checked = []

        def disk_usage(path):
            checked.append(Path(path))
            return types.SimpleNamespace(free=10**12)

        with patch("zhiyeteam.backup.shutil.disk_usage", side_effect=disk_usage):
            create_backup(self.store, target)

        self.assertTrue(target.exists())
        self.assertEqual(checked, [self.path.parent])

    def test_b04_protection_space_failure_stops_before_restore(self):
        note = self.store.create("A", "old")
        source = self._make_backup("source.db")
        self.store.save(note.id, "A", "current")
        protection_dir = self.path.parent / "missing" / "protection"

        with patch(
            "zhiyeteam.backup.shutil.disk_usage",
            return_value=types.SimpleNamespace(free=1),
        ):
            with self.assertRaises(ValidationError):
                restore_backup(self.store, source, protection_dir)

        self.assertEqual(self.store.get(note.id).body, "current")
        self.assertFalse(protection_dir.exists())

    def test_failure_before_protection_records_blank_protection_file(self):
        bad = self.path.parent / "bad.db"
        bad.write_bytes(b"not a database")

        with self.assertRaises(ValidationError):
            restore_with_audit(
                self.store,
                bad,
                self.path.parent / "protect",
                self._audit_path(),
            )

        records = self._records(self._audit_path())
        self.assertEqual(records[-1]["event"], "failed")
        self.assertEqual(records[-1]["error_type"], "ValidationError")
        self.assertEqual(records[-1]["protection_file"], "")
        self.assertFalse(records[-1]["writes_disabled"])

    def test_b05_success_audit_is_correlated_and_private(self):
        note = self.store.create("隐私标题ABC", "隐私正文XYZ")
        source = self._make_backup("old.db")
        self.store.save(note.id, "新标题", "当前正文")
        audit_path = self._audit_path()

        report = restore_with_audit(
            self.store, source, self.path.parent / "protect", audit_path
        )

        self.assertEqual(report.audit_warning, "")
        self.assertTrue(report.protection_path.exists())
        records = self._records(audit_path)
        self.assertEqual([r["event"] for r in records], ["started", "succeeded"])
        self.assertEqual({r["operation_id"] for r in records}, {report.operation_id})
        self.assertEqual(records[-1]["backup_file"], "old.db")
        self.assertEqual(
            records[-1]["protection_file"], report.protection_path.name
        )
        raw = audit_path.read_text(encoding="utf-8")
        self.assertNotIn("隐私正文XYZ", raw)
        self.assertNotIn("隐私标题ABC", raw)
        self.assertNotIn(str(self.path.parent), raw)

    def test_b06_audit_write_failure_does_not_redo_successful_restore(self):
        note = self.store.create("A", "old")
        source = self._make_backup("old.db")
        self.store.save(note.id, "A", "current")

        with patch(
            "zhiyeteam.restore_audit.restore_backup",
            wraps=backup.restore_backup,
        ) as restore_call:
            with patch(
                "zhiyeteam.restore_audit._append_event",
                side_effect=OSError("audit blocked"),
            ):
                report = restore_with_audit(
                    self.store,
                    source,
                    self.path.parent / "protect",
                    self._audit_path(),
                )

        self.assertEqual(report.audit_warning, AUDIT_WARNING)
        self.assertEqual(restore_call.call_count, 1)
        self.assertEqual(self.store.get(note.id).body, "old")
        self.assertTrue(report.protection_path.exists())

    def test_b07_failed_restore_records_failure_without_error_text_or_paths(self):
        note = self.store.create("A", "old")
        source = self._make_backup("old.db")
        self.store.save(note.id, "A", "current")
        real_copy = backup._copy
        calls = []

        def fail_second_copy(src, dst):
            calls.append(1)
            if len(calls) == 2:
                raise OSError("secret path C:/private/notes.db")
            real_copy(src, dst)

        with patch("zhiyeteam.backup._copy", fail_second_copy):
            with self.assertRaises(AppError):
                restore_with_audit(
                    self.store,
                    source,
                    self.path.parent / "protect",
                    self._audit_path(),
                )

        self.assertEqual(self.store.get(note.id).body, "current")
        records = self._records(self._audit_path())
        self.assertEqual(records[-1]["event"], "failed")
        self.assertEqual(records[-1]["error_type"], "AppError")
        self.assertFalse(records[-1]["writes_disabled"])
        self.assertTrue(records[-1]["protection_file"].startswith("恢复前保护_"))
        raw = self._audit_path().read_text(encoding="utf-8")
        self.assertNotIn("C:/private/notes.db", raw)
        self.assertNotIn(str(self.path.parent), raw)

    def test_b07_audit_failure_does_not_mask_original_restore_error(self):
        note = self.store.create("A", "old")
        source = self._make_backup("old.db")
        self.store.save(note.id, "A", "current")
        real_copy = backup._copy
        calls = []

        def fail_second_copy(src, dst):
            calls.append(1)
            if len(calls) == 2:
                raise OSError("restore failed")
            real_copy(src, dst)

        with patch("zhiyeteam.backup._copy", fail_second_copy):
            with patch(
                "zhiyeteam.restore_audit._append_event",
                side_effect=OSError("audit blocked"),
            ):
                with self.assertRaises(AppError) as caught:
                    restore_with_audit(
                        self.store,
                        source,
                        self.path.parent / "protect",
                        self._audit_path(),
                    )

        self.assertIn("恢复未完成", str(caught.exception))
        self.assertEqual(self.store.get(note.id).body, "current")

    def test_b08_double_failure_disables_writes_and_audits_protection(self):
        note = self.store.create("A", "old")
        source = self._make_backup("old.db")
        self.store.save(note.id, "A", "current")
        real_copy = backup._copy
        calls = []

        def fail_after_protection(src, dst):
            calls.append(1)
            if len(calls) > 1:
                raise OSError("restore and rollback failed")
            real_copy(src, dst)

        with patch("zhiyeteam.backup._copy", fail_after_protection):
            with self.assertRaises(AppError):
                restore_with_audit(
                    self.store,
                    source,
                    self.path.parent / "protect",
                    self._audit_path(),
                )

        self.assertTrue(self.store.writes_disabled)
        records = self._records(self._audit_path())
        self.assertEqual(records[-1]["event"], "failed")
        self.assertTrue(records[-1]["writes_disabled"])
        self.assertTrue(records[-1]["protection_file"])
        with self.assertRaises(ValidationError):
            self.store.save(note.id, "A", "new")
