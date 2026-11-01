"""Build on Windows with the project venv; no administrator install required."""
from pathlib import Path
import subprocess,sys,json,hashlib

ROOT=Path(__file__).resolve().parent.parent
venv=ROOT/".venv/Scripts/python.exe"
if not venv.exists():raise SystemExit("请先创建.venv并安装requirements-build.txt")
args=[str(venv),"-m","PyInstaller","--noconfirm","--clean","--onefile","--windowed","--name","ZhiYeTeam","--paths",str(ROOT/"src"),"--add-data",str(ROOT/"src/zhiyeteam/schema.sql")+";zhiyeteam","--add-data",str(ROOT/"src/zhiyeteam/assets/icon.ico")+";zhiyeteam/assets","--icon",str(ROOT/"src/zhiyeteam/assets/icon.ico"),"--collect-all","markdown",str(ROOT/"tools/launch.py")]
subprocess.run(args,cwd=ROOT,check=True)
exe=ROOT/"dist/ZhiYeTeam.exe"
report={"file":exe.name,"bytes":exe.stat().st_size,"sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),"platform":sys.platform,"build_python":subprocess.check_output([str(venv),"--version"],text=True).strip()}
(ROOT/"reports/build.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
