"""Highlight positions refer to plain snippet Unicode code points."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from support import StoreFixture

from zhiyeteam.models import Note
from zhiyeteam.search import SearchHit, search_hits, search_notes
from zhiyeteam.search_presenter import keyword_words, present_hit


STAMP = "2026-11-01T00:00:00.000000+00:00"


class SnippetHighlightTests(unittest.TestCase):
    def hit(self, body, keywords="", title="示例"):
        note = Note("note-id", title, body, (), STAMP, STAMP, 1)
        return present_hit(note, keyword_words(keywords))

    def test_chinese_ascii_case_and_all_occurrences(self):
        hit = self.hit("动态规划 AI ai", "动态规划 aI")
        self.assertEqual(hit.snippet, "动态规划 AI ai")
        self.assertEqual(hit.snippet_highlights, ((0, 4), (5, 7), (8, 10)))

    def test_overlapping_and_adjacent_matches_are_merged(self):
        self.assertEqual(self.hit("ababa", "aba bab").snippet_highlights, ((0, 5),))
        self.assertEqual(self.hit("动态规划AI", "动态规划 AI").snippet_highlights, ((0, 6),))

    def test_duplicate_words_do_not_duplicate_ranges(self):
        self.assertEqual(self.hit("AI AI", "AI ai AI").snippet_highlights, ((0, 2), (3, 5)))

    def test_offsets_follow_whitespace_collapse_and_unicode_code_points(self):
        hit = self.hit("\n 😀\t动态规划\r\n  Ai  ", "动态规划 AI")
        self.assertEqual(hit.snippet, "😀 动态规划 Ai")
        self.assertEqual(hit.snippet_highlights, ((2, 6), (7, 9)))
        self.assertEqual([hit.snippet[start:end] for start, end in hit.snippet_highlights],
                         ["动态规划", "Ai"])

    def test_offsets_include_leading_ellipsis_and_only_visible_words(self):
        hit = self.hit("甲" * 200 + "动态规划" + "乙" * 400 + "AI", "AI 动态规划")
        self.assertEqual(len(hit.snippet), 120)
        self.assertEqual(hit.snippet_highlights, ((31, 35),))
        self.assertEqual(hit.snippet[31:35], "动态规划")

    def test_generated_ellipses_do_not_create_matches(self):
        hit = self.hit("甲" * 200, "…", title="…")
        self.assertEqual(hit.snippet, "甲" * 119 + "…")
        self.assertEqual(hit.snippet_highlights, ())
        hit = self.hit("甲" * 200, "甲…", title="甲…")
        self.assertEqual(hit.snippet_highlights, ())

    def test_original_ellipsis_can_be_highlighted(self):
        hit = self.hit("甲" * 150 + "…" + "乙" * 150, "…")
        self.assertEqual(hit.snippet_highlights, ((31, 32),))
        self.assertEqual(hit.snippet[31:32], "…")

    def test_incomplete_cut_off_keyword_is_not_highlighted(self):
        hit = self.hit("甲" * 200 + "A" * 200, "A" * 200)
        self.assertEqual(hit.matched_fields, {"body"})
        self.assertEqual(len(hit.snippet), 120)
        self.assertEqual(hit.snippet_highlights, ())

    def test_empty_query_body_and_title_only_have_no_snippet_ranges(self):
        for body, query, title in (("AI", " \t ", "标题"), ("", "AI", "AI"),
                                   ("普通正文", "AI", "AI")):
            with self.subTest(body=body, query=query):
                self.assertEqual(self.hit(body, query, title).snippet_highlights, ())

    def test_non_ascii_case_matches_original_search_semantics(self):
        self.assertEqual(self.hit("Å å", "å").snippet_highlights, ((2, 3),))

    def test_html_is_literal_text_without_injected_markup(self):
        hit = self.hit('<script>AI</script>', "ai")
        self.assertEqual(hit.snippet, '<script>AI</script>')
        self.assertEqual(hit.snippet_highlights, ((8, 10),))

    def test_three_argument_constructor_and_immutability_remain_compatible(self):
        hit = self.hit("AI", "ai")
        legacy = SearchHit(hit.note, hit.matched_fields, hit.snippet)
        self.assertEqual(legacy.snippet_highlights, ())
        with self.assertRaises(FrozenInstanceError):
            hit.snippet_highlights = ()


class SearchHighlightIntegrationTests(StoreFixture):
    def test_search_hits_preserve_filters_order_and_original_notes(self):
        with patch("zhiyeteam.store.now", return_value=STAMP):
            body = self.store.create("练习", "😀 AI\n动态规划", ["课程"])
            title = self.store.create("AI 动态规划", "普通正文", ["课程"])
            self.store.create("AI 动态规划 缺标签", "")
        start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        kwargs = dict(updated_from=start, updated_before=start + timedelta(days=1))
        notes = search_notes(self.store, "ai 动态规划", ["课程"], **kwargs)
        hits = search_hits(self.store, "ai 动态规划", ["课程"], **kwargs)
        self.assertEqual([hit.note for hit in hits], notes)
        self.assertEqual([hit.note.id for hit in hits], [title.id, body.id])
        self.assertEqual([hit.snippet for hit in hits], ["普通正文", "😀 AI 动态规划"])
        self.assertEqual([hit.snippet_highlights for hit in hits],
                         [(), ((2, 4), (5, 9))])
