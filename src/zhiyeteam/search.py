"""AND keyword/tag filtering with deterministic title-first ordering."""

import re

from .store import ascii_lower, clean_tags


def search_notes(store, keywords="", tags=(), deleted=False):
    words = [ascii_lower(x) for x in re.split(r"\s+", keywords.strip()) if x]
    wanted = set(clean_tags(tags))
    found = []
    for note in store.list_notes(deleted):
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


def tag_counts(store):
    return [
        (r[0], r[1])
        for r in store.conn.execute(
            "SELECT t.name,count(*) FROM tags t JOIN note_tags nt ON t.id=nt.tag_id JOIN notes n ON n.id=nt.note_id WHERE n.deleted=0 GROUP BY t.id ORDER BY count(*) DESC,t.name"
        )
    ]
