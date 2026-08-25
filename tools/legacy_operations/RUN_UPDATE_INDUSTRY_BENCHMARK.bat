@echo off
cd /d "%~dp0"
python scripts\industry_classifier.py
if errorlevel 1 pause & exit /b 1
python scripts\sector_templates.py
if errorlevel 1 pause & exit /b 1
python scripts\sector_benchmark_engine.py
if errorlevel 1 pause & exit /b 1
echo DONE - Da cap nhat phan nganh va trung binh nganh.
pause
