from support import StoreFixture
from unittest.mock import patch
from zhiyeteam.backup import create_backup,restore_backup,inspect_backup
from zhiyeteam.models import ValidationError,AppError

class BackupTests(StoreFixture):
    def test_roundtrip_includes_versions_and_trash(self):
        a=self.store.create("A","旧内容");b=self.store.create("B","回收站")
        self.store.set_deleted(b.id,True)
        target=self.path.parent/"snapshot.db";create_backup(self.store,target)
        self.store.save(a.id,"A","新内容");self.store.create("C")
        protect=restore_backup(self.store,target,self.path.parent/"protect")
        self.assertEqual(self.store.get(a.id).body,"旧内容")
        self.assertEqual(self.store.stats()["active"],1)
        self.assertTrue(self.store.get(b.id).deleted)
        self.assertEqual(inspect_backup(protect)["notes"],2)
    def test_corrupt_input_never_changes_current(self):
        n=self.store.create("A","keep");bad=self.path.parent/"bad.db";bad.write_bytes(b"not a database")
        with self.assertRaises(ValidationError):restore_backup(self.store,bad,self.path.parent/"p")
        self.assertEqual(self.store.get(n.id).body,"keep")
    def test_existing_target_refused(self):
        target=self.path.parent/"old.db";target.write_bytes(b"keep")
        with self.assertRaises(ValidationError):create_backup(self.store,target)
        self.assertEqual(target.read_bytes(),b"keep")
    def test_failed_copy_rolls_back_from_protection(self):
        from zhiyeteam import backup
        n=self.store.create("A","old");target=self.path.parent/"snapshot.db";create_backup(self.store,target)
        self.store.save(n.id,"A","current")
        real=backup._copy;calls=[]
        def fail_second(src,dst):
            calls.append(1)
            if len(calls)==2:raise OSError("injected restore failure")
            real(src,dst)
        with patch("zhiyeteam.backup._copy",fail_second):
            with self.assertRaises(AppError):restore_backup(self.store,target,self.path.parent/"protection")
        self.assertEqual(self.store.get(n.id).body,"current")
    def test_failed_rollback_disables_future_writes(self):
        from zhiyeteam import backup
        n=self.store.create("A","old");target=self.path.parent/"backup.db";create_backup(self.store,target)
        real=backup._copy;calls=[]
        def fail_after_protection(src,dst):
            calls.append(1)
            if len(calls)>1:raise OSError("injected failure")
            real(src,dst)
        with patch("zhiyeteam.backup._copy",fail_after_protection):
            with self.assertRaises(AppError):restore_backup(self.store,target,self.path.parent/"p")
        self.assertTrue(self.store.writes_disabled)
        with self.assertRaises(ValidationError):self.store.save(n.id,"A","new")
    def test_unknown_schema_is_refused(self):
        import sqlite3
        target=self.path.parent/"altered.db";create_backup(self.store,target)
        con=sqlite3.connect(target);con.execute("CREATE TABLE unexpected(x)");con.commit();con.close()
        with self.assertRaises(ValidationError):inspect_backup(target)
