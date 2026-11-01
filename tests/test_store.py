from support import StoreFixture
from zhiyeteam.store import NoteStore
from zhiyeteam.models import ValidationError,ConflictError

class StoreTests(StoreFixture):
    def test_create_update_persist(self):
        note=self.store.create("课程","原文",["学习"])
        saved=self.store.save(note.id,"新标题","更新",["课程"],note.revision)
        self.assertEqual((saved.id,saved.revision,saved.tags),(note.id,2,("课程",)))
        self.store.close();self.store=NoteStore(self.path)
        self.assertEqual(self.store.get(note.id).body,"更新")
    def test_noop_save_does_not_make_history(self):
        note=self.store.create("A","B")
        self.assertEqual(self.store.save(note.id,"A","B").revision,1)
        self.assertEqual(self.store.stats()["versions"],1)
    def test_empty_title_and_oversize_body_rejected(self):
        for title,body in [(" ","x"),("A","中"*349526)]:
            with self.assertRaises(ValidationError):self.store.create(title,body)
        self.assertEqual(self.store.stats()["active"],0)
    def test_optimistic_conflict_preserves_disk(self):
        note=self.store.create("A","old")
        self.store.save(note.id,"A","new",expected_revision=1)
        with self.assertRaises(ConflictError):self.store.save(note.id,"A","stale",expected_revision=1)
        self.assertEqual(self.store.get(note.id).body,"new")
    def test_failed_tag_validation_is_atomic(self):
        note=self.store.create("A","old")
        with self.assertRaises(ValidationError):self.store.save(note.id,"A","new",["x"*21])
        self.assertEqual(self.store.get(note.id).body,"old")
    def test_settings_roundtrip(self):
        self.store.set_setting("font_size",16);self.assertEqual(self.store.settings("font_size"),16)
    def test_second_connection_cannot_silently_overwrite(self):
        n=self.store.create("A","original")
        other=NoteStore(self.path)
        try:
            other.save(n.id,"A","other window",expected_revision=1)
            with self.assertRaises(ConflictError):self.store.save(n.id,"A","stale window",expected_revision=1)
            self.assertEqual(self.store.get(n.id).body,"other window")
        finally:other.close()
