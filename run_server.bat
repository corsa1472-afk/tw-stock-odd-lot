@echo off
setlocal
cd /d "%~dp0"
echo Starting backend and public tunnel watchdog...
python -u "run_app.py"
pause
