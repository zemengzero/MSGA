import re
import uuid
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Link:
    start: int
    end: int
    target: str
    alias: str | None


def extract_links(body):
    """One shared recognizer for graph, editor preview and export.

    Code fences, inline code and escaped brackets are excluded. This is a
    documented notebook extension, not a claim to implement all CommonMark.
    """
    chars = list(body)
    offset = 0
    fence = None
    for line in body.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        masked = fence is not None or match is not None
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        if masked:
            chars[offset : offset + len(line)] = [
                "\n" if c == "\n" else " " for c in line
            ]
        offset += len(line)
    masked = "".join(chars)
    for match in re.finditer(r"(`+)(.+?)\1", masked, re.DOTALL):
        chars[match.start() : match.end()] = [
            "\n" if c == "\n" else " " for c in match.group()
        ]
    masked = "".join(chars)
    result = []
    for m in re.finditer(r"\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]\n]+))?\]\]", masked):
        prefix = body[: m.start()]
        escapes = len(prefix) - len(prefix.rstrip("\\"))
        if escapes % 2:
            continue
        try:
            target = str(uuid.UUID(m.group(1)))
        except ValueError:
            continue
        result.append(Link(m.start(), m.end(), target, m.group(2)))
    return result


def sync_links(conn, note_id, body):
    conn.execute("DELETE FROM links WHERE source_id=?", (note_id,))
    counts = Counter(link.target for link in extract_links(body))
    conn.executemany(
        "INSERT INTO links VALUES(?,?,?)",
        [(note_id, target, count) for target, count in counts.items()],
    )


def backlinks(store, target_id):
    rows = store.conn.execute(
        "SELECT n.id,l.occurrences FROM links l JOIN notes n ON n.id=l.source_id WHERE l.target_id=? AND n.deleted=0 ORDER BY n.updated_at DESC,n.id",
        (target_id,),
    ).fetchall()
    return [(store.get(r[0]), r[1]) for r in rows]
