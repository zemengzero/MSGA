"""Record the actual full regression run without replacing baseline evidence."""

import hashlib
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from run_checks import EvidenceResult

output = ROOT / "reports/A"
output.mkdir(parents=True, exist_ok=True)
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
with (output / "galaxy-python.log").open("w", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(
        stream=stream, verbosity=2, resultclass=EvidenceResult
    ).run(suite)
data = {
    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version.split()[0],
    "platform": platform.platform(),
    "tests_run": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "skipped": len(result.skipped),
    "passed": result.wasSuccessful(),
    "cases": result.events,
    "source_files_sha256": {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "src/zhiyeteam").glob("*.py"))
    },
}
(output / "galaxy-python.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {k: v for k, v in data.items() if k not in ("cases", "source_files_sha256")},
        ensure_ascii=False,
    )
)
if not result.wasSuccessful():
    raise SystemExit(1)
