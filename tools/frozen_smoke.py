import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
exe = ROOT / "dist/ZhiYeTeam.exe"
run = ROOT / "runtime" / ("frozen-" + uuid.uuid4().hex[:8])
report = ROOT / "reports/frozen_smoke.json"
completed = subprocess.run(
    [
        str(exe),
        "--demo",
        "--data-dir",
        str(run),
        "--smoke-test",
        "--smoke-report",
        str(report),
    ],
    cwd=ROOT,
    timeout=60,
)
assert completed.returncode == 0, (
    completed.returncode,
    report.read_text(encoding="utf-8") if report.exists() else "no report",
)
result = json.loads(report.read_text(encoding="utf-8"))
assert result["passed"] and result["visible"] and result["preview_nonempty"]
result["tested_executable"] = exe.name
result["self_contained_executable_launched"] = True
report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
