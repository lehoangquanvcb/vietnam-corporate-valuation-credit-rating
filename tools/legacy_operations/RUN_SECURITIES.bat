@echo off
cd /d "%~dp0"
python scripts\refresh_vnstock_multisector.py SECURITIES
python scripts\validate_v8.py
pause
