from support import StoreFixture

from zhiyeteam.search import search_notes, tag_counts
from zhiyeteam.store import clean_tags


class SearchTests(StoreFixture):
    def prepare(self):
        a = self.store.create("算法", "AI 动态规划", ["课程", "ai"])
        b = self.store.create("注意力", "AI 模型", ["论文", "ai"])
        c = self.store.create("练习", "动态规划练习", ["课程"])
        d = self.store.create("AI 项目", "开发记录", ["ai"])
        for i, n in enumerate([d, a, b, c]):
            self.store.conn.execute(
                "UPDATE notes SET updated_at=? WHERE id=?",
                (f"2026-01-01T{i + 9:02}:00:00+00:00", n.id),
            )
        self.store.conn.commit()
        return a, b, c, d

    def test_keyword_and_title_priority(self):
        a, b, c, d = self.prepare()
        self.assertEqual(
            [n.id for n in search_notes(self.store, "ai")], [d.id, b.id, a.id]
        )
        self.assertEqual([n.id for n in search_notes(self.store, "ai 动态")], [a.id])

    def test_tags_and_empty_query(self):
        a, b, c, d = self.prepare()
        self.assertEqual(
            [n.id for n in search_notes(self.store, "动态规划", ["课程"])], [c.id, a.id]
        )
        self.assertEqual(
            [n.id for n in search_notes(self.store, "", ["课程", "ai"])], [a.id]
        )
        self.assertEqual(
            [n.id for n in search_notes(self.store)], [c.id, b.id, a.id, d.id]
        )
        self.assertEqual(search_notes(self.store, "不存在"), [])

    def test_tag_normalization_and_counts(self):
        self.assertEqual(clean_tags([" AI ", "ai", "e\u0301", "é"]), ("ai", "é"))
        self.prepare()
        self.assertIn(("ai", 3), tag_counts(self.store))
