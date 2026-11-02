"""Build isolated synthetic C1/C2 acceptance notes; never open an existing DB."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from zhiyeteam.links import backlinks
from zhiyeteam.search import search_hits
from zhiyeteam.store import NoteStore


START = datetime(2026, 11, 1, tzinfo=timezone(timedelta(hours=8)))
END = START + timedelta(days=1)


def build_demo(path):
    """Create a fresh database with fixed note times and print actual results."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=False)
    store = NoteStore(path)
    try:
        ids = {}
        specs = [
            ("target", "状态转移定义", "子问题与转移方程。", ("课程",), START, False),
            ("title_hit", "动态规划 AI 提纲", "记录状态转移。", ("课程", "ai"), START, False),
            ("body_hit", "长文练习", "甲" * 200 + "动态规划" + "乙" * 400
             + "AI\n[[note:{target}]]", ("课程", "ai"), END - timedelta(microseconds=1), False),
            ("before_start", "动态规划 AI 起点外", "边界外。", ("课程", "ai"),
             START - timedelta(microseconds=1), False),
            ("at_end", "动态规划 AI 终点", "终点不包含。", ("课程", "ai"), END, False),
            ("missing_tag", "动态规划 AI 缺标签", "只有一个标签。", ("课程",), START, False),
            ("missing_word", "AI 缺关键词", "普通记录。", ("课程", "ai"), START, False),
            ("trash", "动态规划 AI 回收站", "需要显式查询。", ("课程", "ai"), START, True),
            ("empty", "空正文", "", ("课程", "ai"), START, False),
        ]
        for key, title, body, tags, stamp, deleted in specs:
            if "{target}" in body:
                body = body.replace("{target}", ids["target"])
            note = store.create(title, body, tags)
            ids[key] = note.id
            if deleted:
                store.set_deleted(note.id, True)
            # Only this newly-created synthetic DB is assigned fixed note times.
            utc_stamp = stamp.astimezone(timezone.utc).isoformat(timespec="microseconds")
            with store.conn:
                store.conn.execute(
                    "UPDATE notes SET created_at=?,updated_at=? WHERE id=?",
                    (utc_stamp, utc_stamp, note.id),
                )
        keys = {value: key for key, value in ids.items()}

        def describe(hits):
            return [
                {"key": keys[hit.note.id], "id": hit.note.id, "title": hit.note.title,
                 "matched_fields": sorted(hit.matched_fields),
                 "snippet": hit.snippet, "snippet_length": len(hit.snippet)}
                for hit in hits
            ]

        query = dict(keywords="动态规划 AI", tags=["课程", "ai"],
                     updated_from=START, updated_before=END)
        return {
            "synthetic": True,
            "note_ids": ids,
            "interval": [START.isoformat(), END.isoformat()],
            "active_hits": describe(search_hits(store, **query)),
            "trash_hits": describe(search_hits(store, deleted=True, **query)),
            "target_backlinks": [{"id": n.id, "key": keys[n.id], "count": count}
                                 for n, count in backlinks(store, ids["target"])],
        }
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="New demo database path; existing files are refused")
    args = parser.parse_args()
    if args.database is None:
        root = Path(__file__).resolve().parents[1] / "runtime" / "c-search-demo"
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as directory:
            result = build_demo(Path(directory) / "notes.db")
    else:
        try:
            result = build_demo(args.database)
        except FileExistsError:
            parser.error("数据库已存在；请指定新的演示路径，不覆盖已有笔记")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
