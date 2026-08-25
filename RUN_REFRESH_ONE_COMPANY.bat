@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo ============================================
echo       CAP NHAT 1 DOANH NGHIEP
echo ============================================
set /p TICKER=Nhap ma doanh nghiep (VD: VCB, SSI, HPG): 
if "%TICKER%"=="" goto :end

if exist scripts\refresh_one_company.py (
    %PYTHON% scripts\refresh_one_company.py %TICKER%
) else if exist scripts\refresh_vnstock.py (
    %PYTHON% scripts\refresh_vnstock.py --ticker %TICKER%
) else (
    echo Khong tim thay script refresh 1 doanh nghiep.
    echo Cac BAT cu van duoc luu tai tools\legacy_operations.
    goto :err
)
if errorlevel 1 goto :err

echo Cap nhat benchmark + analyst...
%PYTHON% scripts\sector_benchmark_engine.py
%PYTHON% scripts\intelligent_analyst.py
echo.
echo DONE - %TICKER%
pause
exit /b 0
:err
echo.
echo LOI - xem thong bao phia tren.
pause
exit /b 1
:end
