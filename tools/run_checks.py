"""Write measured test evidence; synthetic fixtures are not user feedback."""

import json
import math
import platform
import sqlite3
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from zhiyeteam.search import search_notes
from zhiyeteam.store import NoteStore


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.events = []

    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test):
        self.events.append(
            {
                "test": test.id(),
                "status": "passed",
                "ms": round((time.perf_counter() - self.started) * 1000, 3),
            }
        )
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.events.append({"test": test.id(), "status": "failed"})
        super().addFailure(test, err)

    def addError(self, test, err):
        self.events.append({"test": test.id(), "status": "error"})
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.events.append({"test": test.id(), "status": "skipped", "reason": reason})
        super().addSkip(test, reason)


def run():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with (reports / "test-log.txt").open("w", encoding="utf-8") as log:
        result = unittest.TextTestRunner(
            stream=log, verbosity=2, resultclass=EvidenceResult
        ).run(suite)
    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.wasSuccessful(),
        "cases": result.events,
    }
    runtime = ROOT / "runtime/benchmark"
    runtime.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=runtime) as temp:
        assert Path(temp).resolve().is_relative_to(runtime.resolve())
        store = NoteStore(Path(temp) / "benchmark.db")
        for i in range(200):
            prefix = f"动态规划 topic{i % 10:02d} 教学检索样本\n"
            body = prefix + "x" * (2048 - len(prefix.encode()))
            store.create(f"测试笔记{i:03}", body, ["课程", f"group{i % 5}"])
        rows = []
        for j in range(30):
            query = (
                "动态规划"
                if j % 3 == 0
                else "不存在"
                if j % 3 == 1
                else f"topic{j % 10:02d}"
            )
            start = time.perf_counter()
            items = search_notes(store, query, ["课程"])
            ms = (time.perf_counter() - start) * 1000
            expected = 200 if j % 3 == 0 else 0 if j % 3 == 1 else 20
            assert len(items) == expected
            rows.append(
                {
                    "sample": j + 1,
                    "query": query,
                    "matches": len(items),
                    "ms": round(ms, 3),
                }
            )
        samples = sorted(r["ms"] for r in rows)
        report["backend_benchmark"] = {
            "notes": 200,
            "utf8_bytes_per_note": 2048,
            "samples": 30,
            "p95_ms": samples[math.ceil(0.95 * 30) - 1],
            "maximum_ms": samples[-1],
            "raw": rows,
            "scope": "后端过滤调用；不是整机界面端到端时延",
        }
        store.close()
    (reports / "test_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["cases", "backend_benchmark"]}
            | {"backend_p95_ms": report["backend_benchmark"]["p95_ms"]},
            ensure_ascii=False,
        )
    )
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    run()
