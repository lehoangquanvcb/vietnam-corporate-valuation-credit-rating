@echo off
cd /d "%~dp0"
set /p TICKER=Nhap ma co phieu:
python scripts\export_professional_report.py %TICKER% analysis
pause
