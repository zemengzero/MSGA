"""Verify the C handoff demo through the same CLI used by another member."""

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "c_search_demo.py"


class CSearchDemoTests(unittest.TestCase):
    def setUp(self):
        root = ROOT / "runtime" / "tests"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "notes.db"

    def run_demo(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=ROOT, capture_output=True, timeout=30,
        )

    def test_persistent_demo_matches_documented_results_and_boundaries(self):
        result = self.run_demo("--database", self.path)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        data = json.loads(result.stdout.decode("utf-8"))
        ids = data["note_ids"]
        self.assertTrue(data["synthetic"])
        self.assertEqual(len(ids), 9)
        self.assertEqual([h["id"] for h in data["active_hits"]],
                         [ids["title_hit"], ids["body_hit"]])
        self.assertEqual([h["matched_fields"] for h in data["active_hits"]],
                         [["title"], ["body"]])
        self.assertEqual(data["active_hits"][0]["snippet"], "记录状态转移。")
        self.assertEqual(data["active_hits"][1]["snippet"],
                         "…" + "甲" * 30 + "动态规划" + "乙" * 84 + "…")
        self.assertEqual([h["snippet_length"] for h in data["active_hits"]], [7, 120])
        self.assertEqual([h["id"] for h in data["trash_hits"]], [ids["trash"]])
        self.assertEqual(data["target_backlinks"],
                         [{"id": ids["body_hit"], "key": "body_hit", "count": 1}])
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM notes").fetchone()[0], 9)
            for key, stamp in (
                ("before_start", "2026-10-31T15:59:59.999999+00:00"),
                ("title_hit", "2026-10-31T16:00:00.000000+00:00"),
                ("body_hit", "2026-11-01T15:59:59.999999+00:00"),
                ("at_end", "2026-11-01T16:00:00.000000+00:00"),
            ):
                with self.subTest(key=key):
                    self.assertEqual(conn.execute(
                        "SELECT updated_at FROM notes WHERE id=?", (ids[key],)
                    ).fetchone()[0], stamp)

    def test_existing_file_is_refused_without_changing_its_contents(self):
        original = b"existing data must not be opened or replaced"
        self.path.write_bytes(original)
        result = self.run_demo("--database", self.path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_bytes(), original)

    def test_default_temporary_demo_emits_json_and_cleans_up(self):
        root = ROOT / "runtime" / "c-search-demo"
        root.mkdir(parents=True, exist_ok=True)
        before = set(root.iterdir())
        result = self.run_demo()
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        data = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual([h["key"] for h in data["active_hits"]], ["title_hit", "body_hit"])
        self.assertEqual(set(root.iterdir()), before)
