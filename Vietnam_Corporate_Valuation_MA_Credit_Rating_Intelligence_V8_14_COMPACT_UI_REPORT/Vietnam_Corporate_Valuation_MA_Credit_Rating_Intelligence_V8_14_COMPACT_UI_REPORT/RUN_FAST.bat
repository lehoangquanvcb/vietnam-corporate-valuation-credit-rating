@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo ============================================
echo        CAP NHAT NHANH - KHONG GOI LAI
echo              TOAN BO VNSTOCK
echo ============================================
echo [1/4] Cap nhat Industry Benchmark...
%PYTHON% scripts\sector_benchmark_engine.py
if errorlevel 1 goto :err
echo [2/4] Intelligent Analyst...
%PYTHON% scripts\intelligent_analyst.py
if errorlevel 1 goto :err
echo [3/4] Decision Intelligence...
%PYTHON% scripts\export_decision_intelligence.py VCB >nul 2>&1
echo [4/4] Validate Python...
%PYTHON% -m py_compile app.py
if errorlevel 1 goto :err
echo.
echo DONE - Cap nhat nhanh hoan tat.
pause
exit /b 0
:err
echo.
echo LOI - xem thong bao phia tren.
pause
exit /b 1
