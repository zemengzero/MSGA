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


def keyword_words(keywords):
    """Use the same whitespace splitting and ASCII folding for all search APIs."""
    return [ascii_lower(word) for word in re.split(r"\s+", keywords.strip()) if word]


def _snippet(body, words):
    text = " ".join(body.split())
    if len(text) <= 120:
        return text
    lowered = ascii_lower(text)
    positions = [position for word in words if (position := lowered.find(word)) >= 0]
    first = min(positions, default=0)
    start = max(0, first - 30)
    prefix = "…" if start else ""
    budget = 120 - len(prefix)
    if len(text) - start <= budget:
        return prefix + text[start:]
    return prefix + text[start : start + budget - 1] + "…"


def present_hit(note, words):
    """Describe actual keyword occurrences, independently of tag/date filters.

    The snippet is at most 120 Unicode code points including ellipses.
    It is a plain string, never rendered or interpreted as HTML here.
    """
    fields = frozenset(
        name
        for name, value in (("title", ascii_lower(note.title)),
                            ("body", ascii_lower(note.body)))
        if any(word in value for word in words)
    )
    return SearchHit(note, fields, _snippet(note.body, words))
