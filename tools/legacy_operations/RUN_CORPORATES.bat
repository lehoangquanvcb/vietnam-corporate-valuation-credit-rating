@echo off
cd /d "%~dp0"
python scripts\refresh_vnstock_multisector.py CORPORATES
python scripts\validate_v8.py
pause
