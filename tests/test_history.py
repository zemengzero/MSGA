from support import StoreFixture

from zhiyeteam.links import backlinks
from zhiyeteam.models import ValidationError


class HistoryTests(StoreFixture):
    def test_trash_restore_keeps_uuid_and_links(self):
        target = self.store.create("目标")
        source = self.store.create("来源", f"[[note:{target.id}]]")
        self.store.set_deleted(target.id, True)
        self.assertTrue(self.store.get(target.id).deleted)
        self.assertEqual(backlinks(self.store, target.id)[0][0].id, source.id)
        self.assertEqual(self.store.set_deleted(target.id, False).id, target.id)

    def test_deleted_source_not_in_backlinks(self):
        target = self.store.create("目标")
        source = self.store.create("来源", f"[[note:{target.id}]]")
        self.store.set_deleted(source.id, True)
        self.assertEqual(backlinks(self.store, target.id), [])

    def test_history_restore_creates_new_version(self):
        note = self.store.create("A", "版本一", ["课程"])
        original = self.store.versions(note.id)[0]
        self.store.save(note.id, "B", "版本二", ["论文"])
        restored = self.store.restore_version(note.id, original["id"], 2)
        self.assertEqual(
            (restored.title, restored.body, restored.revision), ("A", "版本一", 3)
        )
        self.assertEqual(len(self.store.versions(note.id)), 3)
        self.assertIn("回退", self.store.versions(note.id)[0]["action"])

    def test_purge_requires_trash_and_retains_dangling_target(self):
        target = self.store.create("目标")
        source = self.store.create("来源", f"[[note:{target.id}]]")
        with self.assertRaises(ValidationError):
            self.store.purge(target.id)
        self.store.set_deleted(target.id, True)
        self.store.purge(target.id)
        self.assertEqual(len(backlinks(self.store, target.id)), 1)
        with self.assertRaises(ValidationError):
            self.store.get(target.id)
