@echo off
cd /d "%~dp0"
set /p TICKER=Nhap ma co phieu:
python scripts\export_analysis_payload.py %TICKER%
pause
