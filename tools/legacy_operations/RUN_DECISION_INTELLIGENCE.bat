@echo off
cd /d "%~dp0"
set /p TICKER=Nhap ma doanh nghiep:
python scripts\export_decision_intelligence.py %TICKER%
pause
