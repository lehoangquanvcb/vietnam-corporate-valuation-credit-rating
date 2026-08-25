@echo off
setlocal
cd /d "%~dp0"
echo [1/5] Phat hien toan bo HOSE/HNX/UPCoM...
python scripts\discover_listed_universe.py
if errorlevel 1 goto :err
echo [2/5] Tu dong phan nganh ICB tu Vnstock...
python scripts\industry_classifier.py
if errorlevel 1 goto :err
echo [3/6] Gan mau phan tich chuyen nganh...
python scripts\sector_templates.py
if errorlevel 1 goto :err
echo [4/6] Tao Coverage Matrix...
python scripts\coverage_engine.py
if errorlevel 1 goto :err
echo [5/6] Tinh trung binh nganh...
python scripts\sector_benchmark_engine.py
if errorlevel 1 goto :err
echo [6/6] Kiem tra package...
python scripts\validate_v8.py
if errorlevel 1 goto :err
echo.
echo DONE - Universe + ICB Industry + Industry Benchmark da cap nhat.
pause
exit /b 0
:err
echo ERROR - xem thong bao phia tren.
pause
exit /b 1
