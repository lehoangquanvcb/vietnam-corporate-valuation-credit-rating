@echo off
cd /d "%~dp0"
set /p TICKER=Nhap ma doanh nghiep:
python scripts\export_professional_report.py %TICKER% rating
pause
