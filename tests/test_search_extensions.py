"""C1 date-filter checks with fixed timestamps, independent of the clock."""

from datetime import date, datetime, timedelta, timezone, tzinfo

from support import StoreFixture

from zhiyeteam.models import Note, ValidationError
from zhiyeteam.search import search_hits, search_notes


UTC = timezone.utc
BEIJING = timezone(timedelta(hours=8))
START = datetime(2026, 11, 1, tzinfo=BEIJING)
END = START + timedelta(days=1)


class NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None


class SearchDateTests(StoreFixture):
    def note(self, title, stamp, body="动态规划 AI", tags=("课程", "ai"), deleted=False):
        note = self.store.create(title, body, tags)
        if deleted:
            self.store.set_deleted(note.id, True)
        self.store.conn.execute(
            "UPDATE notes SET updated_at=? WHERE id=?",
            (stamp.astimezone(UTC).isoformat(timespec="microseconds"), note.id),
        )
        self.store.conn.commit()
        return self.store.get(note.id)

    def ids(self, *args, **kwargs):
        return [note.id for note in search_notes(self.store, *args, **kwargs)]

    def test_default_and_explicit_none_keep_notes_and_original_order(self):
        body_hit = self.note("正文命中", END)
        title_hit = self.note("AI 标题", START)
        expected = [title_hit.id, body_hit.id]
        result = search_notes(self.store, "ai", ["课程"], False)
        self.assertEqual([n.id for n in result], expected)
        self.assertTrue(all(isinstance(n, Note) for n in result))
        self.assertEqual(
            result,
            search_notes(self.store, "ai", ["课程"], False,
                         updated_from=None, updated_before=None),
        )
        self.assertEqual(self.ids(), [body_hit.id, title_hit.id])

    def test_half_open_interval_includes_microseconds(self):
        delta = timedelta(microseconds=1)
        self.note("起点外", START - delta)
        first = self.note("起点", START)
        middle = self.note("起点后一微秒", START + delta)
        last = self.note("终点前一微秒", END - delta)
        self.note("终点", END)
        self.note("终点外", END + delta)
        self.assertEqual(
            self.ids(updated_from=START, updated_before=END),
            [last.id, middle.id, first.id],
        )
        self.assertEqual(
            self.ids(updated_from=START + delta, updated_before=START + 2 * delta),
            [middle.id],
        )

    def test_equivalent_timezones_and_beijing_midnight(self):
        self.note("北京时间前一天", START - timedelta(microseconds=1))
        first = self.note("北京时间当天", START)
        last = self.note("北京时间当晚", END - timedelta(microseconds=1))
        self.note("北京时间后一天", END)
        expected = [last.id, first.id]
        self.assertEqual(self.ids(updated_from=START, updated_before=END), expected)
        self.assertEqual(
            self.ids(updated_from=START.astimezone(UTC),
                     updated_before=END.astimezone(UTC)), expected,
        )

    def test_each_bound_can_be_used_alone(self):
        early = self.note("早", START - timedelta(microseconds=1))
        first = self.note("中", START)
        late = self.note("晚", END)
        self.assertEqual(self.ids(updated_from=START), [late.id, first.id])
        self.assertEqual(self.ids(updated_before=START), [early.id])

    def test_invalid_bounds_raise_validation_error_even_for_empty_store(self):
        for value in ("2026-11-01", date(2026, 11, 1), 0, False, [],
                      datetime(2026, 11, 1), datetime(2026, 11, 1, tzinfo=NoOffset())):
            for name in ("updated_from", "updated_before"):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValidationError):
                        search_notes(self.store, **{name: value})

    def test_equal_and_reversed_intervals_rejected_after_utc_conversion(self):
        for upper in (START, START.astimezone(UTC), START - timedelta(microseconds=1)):
            with self.subTest(upper=upper):
                with self.assertRaises(ValidationError):
                    search_notes(self.store, updated_from=START, updated_before=upper)

    def test_utc_conversion_overflow_raises_validation_error_for_both_apis(self):
        values = (
            datetime.min.replace(tzinfo=BEIJING),
            datetime.max.replace(tzinfo=timezone(timedelta(hours=-12))),
        )
        for api in (search_notes, search_hits):
            for name in ("updated_from", "updated_before"):
                for value in values:
                    with self.subTest(api=api.__name__, name=name, value=value):
                        with self.assertRaisesRegex(ValidationError, name):
                            api(self.store, **{name: value})

    def test_representable_extreme_dates_remain_valid_for_both_apis(self):
        note = self.note("普通笔记", START)
        intervals = (
            (datetime.min.replace(tzinfo=UTC), datetime.max.replace(tzinfo=UTC)),
            (datetime.min.replace(tzinfo=timezone(timedelta(hours=-8))),
             datetime.max.replace(tzinfo=BEIJING)),
        )
        for lower, upper in intervals:
            with self.subTest(lower=lower, upper=upper):
                self.assertEqual(
                    self.ids(updated_from=lower, updated_before=upper), [note.id]
                )
                self.assertEqual(
                    [hit.note.id for hit in search_hits(
                        self.store, updated_from=lower, updated_before=upper
                    )], [note.id],
                )

    def test_keywords_tags_and_dates_intersect_with_title_priority(self):
        title = self.note("AI 动态规划", START)
        body = self.note("正文命中", END - timedelta(microseconds=1))
        self.note("AI 动态规划 缺标签", START, tags=("课程",))
        self.note("AI 缺关键词", START, body="其他")
        self.note("AI 动态规划 区间外", END)
        self.assertEqual(
            self.ids("aI 动态规划", ["课程", "AI"],
                     updated_from=START, updated_before=END),
            [title.id, body.id],
        )
        self.assertEqual(self.ids("不存在", updated_from=START), [])

    def test_dates_only_keep_time_descending_and_id_tiebreaker(self):
        older = self.note("AI 动态规划", START)
        a = self.note("普通标题甲", START + timedelta(hours=1))
        b = self.note("普通标题乙", START + timedelta(hours=1))
        self.assertEqual(
            self.ids(updated_from=START, updated_before=END),
            sorted([a.id, b.id]) + [older.id],
        )

    def test_deleted_flag_still_selects_trash(self):
        active = self.note("有效", START)
        trash = self.note("已删", START, deleted=True)
        self.note("区间外已删", END, deleted=True)
        self.assertEqual(self.ids(updated_from=START, updated_before=END), [active.id])
        self.assertEqual(
            self.ids("", (), True, updated_from=START, updated_before=END), [trash.id],
        )

    def test_date_parameters_are_keyword_only(self):
        with self.assertRaises(TypeError):
            search_notes(self.store, "", (), False, START, END)
