@echo off
cd /d "%~dp0"
if exist "dist\ZhiYeTeam.exe" (
    start "" "dist\ZhiYeTeam.exe" --demo
) else (
    ".venv\Scripts\python.exe" -m zhiyeteam --demo
)
