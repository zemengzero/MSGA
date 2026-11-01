from support import StoreFixture

from zhiyeteam.links import backlinks, extract_links


class LinkTests(StoreFixture):
    def test_rename_keeps_target_id_and_occurrence_count(self):
        target = self.store.create("旧标题")
        token = f"[[note:{target.id}]]"
        source = self.store.create("引用者", token + "\n" + token)
        self.store.save(target.id, "新标题", "")
        self.assertEqual(
            [(n.id, c) for n, c in backlinks(self.store, target.id)], [(source.id, 2)]
        )
        self.assertEqual(
            extract_links(self.store.get(source.id).body)[0].target, target.id
        )

    def test_code_and_escaped_markers_excluded(self):
        n = self.store.create("A")
        token = f"[[note:{n.id}|别名]]"
        body = token + "\n`" + token + "`\n```python\n" + token + "\n```\n\\" + token
        self.assertEqual(len(extract_links(body)), 1)
        self.assertEqual(extract_links(body)[0].alias, "别名")

    def test_graph_failure_rolls_back_note_and_history(self):
        note = self.store.create("A", "old")
        original = self.store._sync_links

        def fail(*_):
            raise RuntimeError("injected graph failure")

        self.store._sync_links = fail
        with self.assertRaises(RuntimeError):
            self.store.save(note.id, "A", "new")
        self.store._sync_links = original
        self.assertEqual(self.store.get(note.id).body, "old")
        self.assertEqual(self.store.get(note.id).revision, 1)
