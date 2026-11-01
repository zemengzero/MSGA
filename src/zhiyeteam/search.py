"""AND keyword/tag filtering with deterministic title-first ordering."""

from datetime import datetime, timezone

from .models import ValidationError
from .search_presenter import SearchHit, keyword_words, present_hit
from .store import ascii_lower, clean_tags


def _utc_bound(value, name):
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValidationError(f"{name}必须是带时区的datetime")
    if value.utcoffset() is None:
        raise ValidationError(f"{name}必须包含时区")
    return value.astimezone(timezone.utc)


def search_notes(
    store,
    keywords="",
    tags=(),
    deleted=False,
    *,
    updated_from: datetime | None = None,
    updated_before: datetime | None = None,
):
    """Return Notes in the original order, optionally within [from, before).

    Bounds must be timezone-aware datetimes; comparison uses UTC instants.
    Either bound may be omitted. Existing positional arguments remain valid.
    """
    updated_from = _utc_bound(updated_from, "updated_from")
    updated_before = _utc_bound(updated_before, "updated_before")
    if (
        updated_from is not None
        and updated_before is not None
        and updated_from >= updated_before
    ):
        raise ValidationError("更新时间起点必须早于终点")
    words = keyword_words(keywords)
    wanted = set(clean_tags(tags))
    found = []
    for note in store.list_notes(deleted):
        if updated_from is not None or updated_before is not None:
            updated_at = datetime.fromisoformat(note.updated_at).astimezone(timezone.utc)
            if updated_from is not None and updated_at < updated_from:
                continue
            if updated_before is not None and updated_at >= updated_before:
                continue
        title = ascii_lower(note.title)
        haystack = title + "\n" + ascii_lower(note.body)
        if not all(w in haystack for w in words) or not wanted.issubset(set(note.tags)):
            continue
        title_hit = bool(words) and any(w in title for w in words)
        found.append((title_hit, note))
    found.sort(key=lambda pair: pair[1].id)
    found.sort(key=lambda pair: pair[1].updated_at, reverse=True)
    found.sort(key=lambda pair: pair[0], reverse=True)
    return [n for _, n in found]


def search_hits(
    store,
    keywords="",
    tags=(),
    deleted=False,
    *,
    updated_from: datetime | None = None,
    updated_before: datetime | None = None,
) -> list[SearchHit]:
    """Return presentation data for the exact search_notes results and order."""
    notes = search_notes(
        store, keywords, tags, deleted,
        updated_from=updated_from, updated_before=updated_before,
    )
    words = keyword_words(keywords)
    return [present_hit(note, words) for note in notes]


def tag_counts(store):
    return [
        (r[0], r[1])
        for r in store.conn.execute(
            "SELECT t.name,count(*) FROM tags t JOIN note_tags nt ON t.id=nt.tag_id JOIN notes n ON n.id=nt.note_id WHERE n.deleted=0 GROUP BY t.id ORDER BY count(*) DESC,t.name"
        )
    ]
