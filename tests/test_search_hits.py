"""C2 results and snippet contracts, with fixed note timestamps."""

from datetime import datetime, timedelta, timezone

from support import StoreFixture

from zhiyeteam.models import Note, ValidationError
from zhiyeteam.search import SearchHit, search_hits, search_notes


START = datetime(2026, 11, 1, tzinfo=timezone(timedelta(hours=8)))
END = START + timedelta(days=1)


class SearchHitTests(StoreFixture):
    def note(self, title, body="", tags=(), stamp=START, deleted=False):
        note = self.store.create(title, body, tags)
        if deleted:
            self.store.set_deleted(note.id, True)
        self.store.conn.execute(
            "UPDATE notes SET updated_at=? WHERE id=?",
            (stamp.astimezone(timezone.utc).isoformat(timespec="microseconds"), note.id),
        )
        self.store.conn.commit()
        return self.store.get(note.id)

    def test_hits_reuse_note_results_for_all_filters_and_order(self):
        title = self.note("AI 动态规划", "算法课", ["课程", "ai"])
        body = self.note("练习", "动态规划 ai", ["课程", "ai"], START + timedelta(hours=1))
        self.note("AI 动态规划", "区间外", ["课程", "ai"], END)
        self.note("AI 动态规划", "缺标签", ["课程"])
        self.note("回收站", "动态规划 ai", ["课程", "ai"], deleted=True)
        for keywords, tags, deleted, bounds in (
            ("", (), False, {}),
            ("aI 动态规划", ["课程", "AI"], False,
             {"updated_from": START, "updated_before": END}),
            ("ai", (), True, {"updated_from": START}),
            ("", ["课程"], False, {"updated_before": END}),
        ):
            with self.subTest(keywords=keywords, deleted=deleted, bounds=bounds):
                hits = search_hits(self.store, keywords, tags, deleted, **bounds)
                notes = search_notes(self.store, keywords, tags, deleted, **bounds)
                self.assertEqual([hit.note for hit in hits], notes)
                self.assertTrue(all(isinstance(hit, SearchHit) for hit in hits))
                self.assertTrue(all(isinstance(note, Note) for note in notes))
        hits = search_hits(self.store, "aI 动态规划", ["课程", "AI"],
                           updated_from=START, updated_before=END)
        self.assertEqual([hit.note.id for hit in hits], [title.id, body.id])

    def test_fields_report_any_actual_keyword_in_each_field(self):
        note = self.note("AI 入门", "动态规划\nAi 案例", ["课程"])
        hit, = search_hits(self.store, "ai 动态规划", ["课程"])
        self.assertEqual(hit.note, note)
        self.assertEqual(hit.matched_fields, frozenset({"title", "body"}))
        self.assertEqual(hit.snippet, "动态规划 Ai 案例")

    def test_title_only_uses_body_start(self):
        self.note("动态规划", "前" * 150)
        hit, = search_hits(self.store, "动态规划")
        self.assertEqual(hit.matched_fields, {"title"})
        self.assertEqual(hit.snippet, "前" * 119 + "…")

    def test_body_hit_is_centered_after_collapsing_whitespace(self):
        self.note("练习", "甲" * 200 + "\n\t动态规划  案例\r\n" + "乙" * 200)
        hit, = search_hits(self.store, "动态规划")
        self.assertEqual(hit.matched_fields, {"body"})
        self.assertEqual(hit.snippet, "…" + "甲" * 29 + " 动态规划 案例 " + "乙" * 80 + "…")
        self.assertEqual(len(hit.snippet), 120)

    def test_first_body_occurrence_wins_over_query_word_order(self):
        self.note("长文", "甲" * 200 + "动态规划" + "乙" * 400 + "AI")
        hit, = search_hits(self.store, "AI 动态规划")
        self.assertEqual(hit.matched_fields, {"body"})
        self.assertEqual(hit.snippet, "…" + "甲" * 30 + "动态规划" + "乙" * 84 + "…")
        self.assertNotIn("AI", hit.snippet)
        self.assertEqual(len(hit.snippet), 120)

    def test_match_near_end_only_needs_leading_ellipsis(self):
        self.note("长文", "甲" * 300 + "aI")
        hit, = search_hits(self.store, "AI")
        self.assertEqual(hit.snippet, "…" + "甲" * 30 + "aI")

    def test_empty_keywords_and_tags_do_not_create_keyword_fields(self):
        self.note("课程", "\n 第一段 \t  第二段\r\n", ["课程"])
        hit, = search_hits(self.store, " \t\n", ["课程"])
        self.assertEqual(hit.matched_fields, frozenset())
        self.assertEqual(hit.snippet, "第一段 第二段")
        self.assertEqual(search_hits(self.store, "课程", ["课程"])[0].matched_fields,
                         {"title"})
        self.assertEqual(search_hits(self.store, "缺少关键词", ["课程"]), [])

    def test_empty_and_whitespace_only_bodies(self):
        for body in ("", " \t\n\r "):
            with self.subTest(body=body):
                note = self.note("AI", body)
                hit = next(h for h in search_hits(self.store, "ai") if h.note.id == note.id)
                self.assertEqual(hit.matched_fields, {"title"})
                self.assertEqual(hit.snippet, "")

    def test_unicode_length_boundary_and_emoji(self):
        for body, expected in (
            ("中" * 120, "中" * 120),
            ("😀" * 121, "😀" * 119 + "…"),
        ):
            with self.subTest(length=len(body)):
                note = self.note("边界", body)
                hit = next(h for h in search_hits(self.store) if h.note.id == note.id)
                self.assertEqual(hit.snippet, expected)
                self.assertEqual(len(hit.snippet), 120)

    def test_html_like_content_remains_literal_plain_text(self):
        self.note("示例", '<script>alert("AI")</script>\n<b>动态规划</b>')
        hit, = search_hits(self.store, "ai")
        self.assertIsInstance(hit.snippet, str)
        self.assertEqual(hit.snippet, '<script>alert("AI")</script> <b>动态规划</b>')
        self.assertEqual(hit.matched_fields, {"body"})

    def test_non_ascii_case_is_not_folded(self):
        self.note("Å", "")
        self.assertEqual(search_hits(self.store, "å"), [])
        self.assertEqual(search_hits(self.store, "Å")[0].matched_fields, {"title"})

    def test_invalid_dates_still_raise_from_shared_search(self):
        for bounds in (
            {"updated_from": "2026-11-01"},
            {"updated_before": datetime(2026, 11, 1)},
            {"updated_from": END, "updated_before": START},
        ):
            with self.subTest(bounds=bounds):
                with self.assertRaises(ValidationError):
                    search_hits(self.store, **bounds)

    def test_no_results(self):
        self.assertEqual(search_hits(self.store), [])
        self.note("无关", "正文")
        self.assertEqual(search_hits(self.store, "不存在"), [])
