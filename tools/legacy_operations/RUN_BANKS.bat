@echo off
cd /d "%~dp0"
python scripts\refresh_vnstock.py || exit /b 1
python scripts\validate_v8.py
pause
