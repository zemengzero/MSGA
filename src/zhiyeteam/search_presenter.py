"""Plain-text search presentation; filtering remains in search_notes."""

import re
from dataclasses import dataclass

from .models import Note
from .store import ascii_lower


@dataclass(frozen=True)
class SearchHit:
    note: Note
    matched_fields: frozenset[str]
    snippet: str
    # Half-open Unicode code-point offsets into snippet; safe for text widgets.
    snippet_highlights: tuple[tuple[int, int], ...] = ()


def keyword_words(keywords):
    """Use the same whitespace splitting and ASCII folding for all search APIs."""
    return [ascii_lower(word) for word in re.split(r"\s+", keywords.strip()) if word]


def _snippet_parts(body, words):
    """Keep generated ellipses separate so they cannot become keyword hits."""
    text = " ".join(body.split())
    if len(text) <= 120:
        return "", text, ""
    lowered = ascii_lower(text)
    positions = [position for word in words if (position := lowered.find(word)) >= 0]
    first = min(positions, default=0)
    start = max(0, first - 30)
    prefix = "…" if start else ""
    budget = 120 - len(prefix)
    if len(text) - start <= budget:
        return prefix, text[start:], ""
    return prefix, text[start : start + budget - 1], "…"


def _snippet(body, words):
    return "".join(_snippet_parts(body, words))


def _highlight_ranges(text, words, offset=0):
    """Merge all complete visible occurrences, including overlapping matches."""
    lowered = ascii_lower(text)
    intervals = []
    for word in set(words):
        if not word:
            continue
        start = lowered.find(word)
        while start >= 0:
            intervals.append((offset + start, offset + start + len(word)))
            start = lowered.find(word, start + 1)
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def present_hit(note, words):
    """Describe actual keyword occurrences, independently of tag/date filters.

    The snippet is at most 120 Unicode code points including ellipses.
    It is a plain string, never rendered or interpreted as HTML here.
    Highlight ranges reference the final snippet, excluding generated ellipses
    and incomplete keywords cut by its boundaries.
    """
    fields = frozenset(
        name
        for name, value in (("title", ascii_lower(note.title)),
                            ("body", ascii_lower(note.body)))
        if any(word in value for word in words)
    )
    prefix, excerpt, suffix = _snippet_parts(note.body, words)
    return SearchHit(
        note, fields, prefix + excerpt + suffix,
        _highlight_ranges(excerpt, words, offset=len(prefix)),
    )
