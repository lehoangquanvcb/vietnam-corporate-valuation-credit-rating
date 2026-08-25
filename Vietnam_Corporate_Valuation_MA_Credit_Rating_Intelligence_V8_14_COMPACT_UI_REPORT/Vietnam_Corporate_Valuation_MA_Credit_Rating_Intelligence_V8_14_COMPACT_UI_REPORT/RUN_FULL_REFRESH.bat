@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo ============================================
echo          FULL REFRESH TOAN THI TRUONG
echo ============================================
echo Luong: Universe -> ICB -> Fundamentals/Prices -> Coverage
echo       -> Industry Benchmark -> Vnstock Cross-check
echo       -> Intelligent Analyst -> Validation
echo.

echo [1/8] Phat hien universe niem yet...
if exist scripts\discover_listed_universe.py (
    %PYTHON% scripts\discover_listed_universe.py
    if errorlevel 1 goto :err
) else (
    echo SKIP - khong co discover_listed_universe.py
)

echo [2/8] Tu dong phan nganh ICB...
if exist scripts\industry_classifier.py (
    %PYTHON% scripts\industry_classifier.py
    if errorlevel 1 goto :err
) else (
    echo SKIP - khong co industry_classifier.py
)

echo [3/8] Refresh du lieu Vnstock...
if exist scripts\refresh_vnstock.py (
    %PYTHON% scripts\refresh_vnstock.py
    if errorlevel 1 goto :err
) else (
    echo SKIP - khong co refresh_vnstock.py.
    echo Neu package cu dung BAT refresh rieng, xem tools\legacy_operations.
)

echo [4/8] Coverage Matrix...
if exist scripts\coverage_engine.py (
    %PYTHON% scripts\coverage_engine.py
    if errorlevel 1 goto :err
)

echo [5/8] Industry Benchmark...
%PYTHON% scripts\sector_benchmark_engine.py
if errorlevel 1 goto :err

echo [6/8] Vnstock peer cross-check...
if exist scripts\refresh_vnstock_peer_crosscheck.py (
    %PYTHON% scripts\refresh_vnstock_peer_crosscheck.py
    if errorlevel 1 echo CANH BAO - Peer cross-check that bai, tiep tuc.
)

echo [7/8] Intelligent Analyst...
%PYTHON% scripts\intelligent_analyst.py
if errorlevel 1 goto :err

echo [8/8] Validation...
if exist scripts\validate_v8.py (
    %PYTHON% scripts\validate_v8.py
    if errorlevel 1 goto :err
) else (
    %PYTHON% -m py_compile app.py
    if errorlevel 1 goto :err
)

echo.
echo DONE - Full refresh hoan tat.
pause
exit /b 0

:err
echo.
echo LOI - Full refresh dung tai buoc tren.
pause
exit /b 1
