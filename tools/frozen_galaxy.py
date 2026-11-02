"""Run the actual bundled executable with a fresh, isolated demo library."""

import hashlib
import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
exe = ROOT / "dist/ZhiYeGalaxy.exe"
report = ROOT / "reports/A/galaxy-frozen.json"
data = ROOT / "runtime" / ("galaxy-frozen-" + uuid.uuid4().hex[:10])
process = subprocess.Popen(
    [str(exe), "--demo", "--data-dir", str(data), "--smoke-report", str(report)],
    cwd=ROOT,
)
try:
    result = process.wait(timeout=80)
except subprocess.TimeoutExpired:
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True
    )
    raise
assert result == 0, (
    result,
    report.read_text(encoding="utf-8") if report.exists() else "no report",
)
value = json.loads(report.read_text(encoding="utf-8"))
assert value["passed"] and value["native_window"] and value["canvas_present"]
value["tested_executable"] = exe.name
value["process_exit_code"] = result
value["exe_sha256"] = hashlib.sha256(exe.read_bytes()).hexdigest()
report.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(value, ensure_ascii=False))
