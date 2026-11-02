"""C3: search/link integration regressions with deterministic IDs and times."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID

from support import StoreFixture

from zhiyeteam.links import backlinks, extract_links
from zhiyeteam.search import search_hits, search_notes


START = datetime(2026, 11, 1, tzinfo=timezone(timedelta(hours=8)))
END = START + timedelta(days=1)
STAMP = START.astimezone(timezone.utc).isoformat(timespec="microseconds")


class SearchLinkRegressionTests(StoreFixture):
    def setUp(self):
        super().setUp()
        clock = patch("zhiyeteam.store.now", return_value=STAMP)
        clock.start()
        self.addCleanup(clock.stop)
        self.next_id = 1

    def note(self, title, body="", tags=("课程", "ai"), stamp=START):
        with patch("zhiyeteam.store.uuid.uuid4", return_value=UUID(int=self.next_id)):
            self.next_id += 1
            note = self.store.create(title, body, tags)
        self.store.conn.execute(
            "UPDATE notes SET created_at=?,updated_at=? WHERE id=?",
            (stamp.astimezone(timezone.utc).isoformat(timespec="microseconds"),) * 2
            + (note.id,),
        )
        self.store.conn.commit()
        return self.store.get(note.id)

    def hits(self, keywords="动态规划 AI", deleted=False):
        return search_hits(
            self.store, keywords, ["课程", "AI"], deleted,
            updated_from=START, updated_before=END,
        )

    def test_combined_filters_keep_title_priority_time_and_id_order(self):
        title = self.note("动态规划 AI", "标题命中")
        first = self.note("练习甲", "动态规划\nAI", stamp=END - timedelta(microseconds=1))
        second = self.note("练习乙", "动态规划 AI", stamp=END - timedelta(microseconds=1))
        self.note("动态规划 AI 早", stamp=START - timedelta(microseconds=1))
        self.note("动态规划 AI 晚", stamp=END)
        self.note("动态规划 AI 缺标签", tags=("课程",))
        self.note("动态规划 缺词", "其他内容")
        hits = self.hits()
        self.assertEqual([hit.note.id for hit in hits], [title.id, first.id, second.id])
        self.assertEqual([hit.matched_fields for hit in hits], [{"title"}, {"body"}, {"body"}])
        self.assertEqual([hit.snippet for hit in hits], ["标题命中", "动态规划 AI", "动态规划 AI"])
        self.assertEqual(
            [hit.note for hit in hits],
            search_notes(self.store, "动态规划 AI", ["课程", "AI"],
                         updated_from=START.astimezone(timezone.utc),
                         updated_before=END.astimezone(timezone.utc)),
        )

    def test_keywords_split_across_title_and_body_still_form_and(self):
        note = self.note("AI 提纲", "\n动态规划\t\u3000案例\n")
        hit, = self.hits(" aI\u00a0动态规划 ")
        self.assertEqual(hit.note.id, note.id)
        self.assertEqual(hit.matched_fields, {"title", "body"})
        self.assertEqual(hit.snippet, "动态规划 案例")
        self.assertEqual(len(hit.snippet), 7)

    def test_distant_words_and_empty_query_with_linked_long_body(self):
        target = self.note("定义")
        token = f"[[note:{target.id}]]"
        source = self.note("长文", "甲" * 200 + "动态规划" + "乙" * 400 + "AI " + token)
        hit, = self.hits("AI 动态规划")
        self.assertEqual(hit.note.id, source.id)
        self.assertEqual(hit.snippet, "…" + "甲" * 30 + "动态规划" + "乙" * 84 + "…")
        self.assertEqual(len(hit.snippet), 120)
        self.assertNotIn("AI", hit.snippet)
        self.assertEqual([(n.id, count) for n, count in backlinks(self.store, target.id)],
                         [(source.id, 1)])
        empty_hits = self.hits("")
        self.assertEqual([h.note.id for h in empty_hits], [target.id, source.id])
        self.assertTrue(all(h.matched_fields == frozenset() for h in empty_hits))
        self.assertEqual(empty_hits[0].snippet, "")
        self.assertEqual(empty_hits[1].snippet, "甲" * 119 + "…")
        self.assertEqual(self.hits("不存在"), [])

    def test_target_rename_and_trash_restore_preserve_uuid_and_search(self):
        target = self.note("旧标题")
        token = f"[[note:{target.id}|定义]]"
        source = self.note("动态规划 AI", "参考 " + token)
        self.store.save(target.id, "新标题", "")
        for deleted in (True, False):
            with self.subTest(deleted=deleted):
                changed = self.store.set_deleted(target.id, deleted)
                self.assertEqual(changed.id, target.id)
                self.assertEqual(self.store.get(target.id).title, "新标题")
                self.assertEqual([(n.id, c) for n, c in backlinks(self.store, target.id)],
                                 [(source.id, 1)])
                hit, = self.hits()
                self.assertEqual(hit.note.id, source.id)
                self.assertEqual(hit.snippet, "参考 " + token)
                self.assertEqual(extract_links(hit.note.body)[0].target, target.id)

    def test_source_trash_restore_keeps_search_and_backlinks_in_sync(self):
        target = self.note("目标")
        first = self.note("动态规划 AI 甲", f"[[note:{target.id}]]")
        second = self.note("动态规划 AI 乙", f"[[note:{target.id}]]")
        self.store.set_deleted(first.id, True)
        self.assertEqual([h.note.id for h in self.hits()], [second.id])
        self.assertEqual([h.note.id for h in self.hits(deleted=True)], [first.id])
        self.assertEqual([(n.id, c) for n, c in backlinks(self.store, target.id)], [(second.id, 1)])
        restored = self.store.set_deleted(first.id, False)
        self.assertEqual(restored.id, first.id)
        self.assertEqual([h.note.id for h in self.hits()], [first.id, second.id])
        self.assertEqual(self.hits(deleted=True), [])
        self.assertEqual([(n.id, c) for n, c in backlinks(self.store, target.id)],
                         [(first.id, 1), (second.id, 1)])

    def test_code_and_escape_recognition_agrees_with_persisted_graph(self):
        target = self.note("目标")
        token = f"[[note:{target.id}|别名]]"
        examples = (
            (token, 1),
            ("`" + token + "`", 0),
            ("``" + token + "``", 0),
            ("```python\n" + token + "\n```", 0),
            ("~~~text\n" + token + "\n~~~", 0),
            ("\\" + token, 0),
            ("\\\\" + token, 1),
            ("\\\\\\" + token, 0),
        )
        expected = []
        for index, (body, count) in enumerate(examples):
            with self.subTest(index=index):
                source = self.note(f"动态规划 AI {index}", body)
                links = extract_links(body)
                self.assertEqual([link.target for link in links], [target.id] * count)
                if count:
                    expected.append((source.id, count))
                self.assertEqual([(n.id, c) for n, c in backlinks(self.store, target.id)], expected)
        # Literal text is searchable even when a marker is excluded from the graph.
        self.assertEqual(len(self.hits(target.id)), len(examples))

    def test_repeated_real_links_ignore_code_and_escaped_occurrences(self):
        target = self.note("目标")
        token = f"[[note:{target.id}]]"
        source = self.note("动态规划 AI", "\n".join(
            [token, "`" + token + "`", "\\" + token, token,
             "```\n" + token + "\n```"]
        ))
        self.assertEqual([(n.id, c) for n, c in backlinks(self.store, target.id)], [(source.id, 2)])
        self.assertEqual(len(extract_links(source.body)), 2)
        hit, = self.hits()
        self.assertEqual(hit.note.id, source.id)
        self.assertEqual(hit.matched_fields, {"title"})
        self.assertEqual(len(hit.snippet), 120)
