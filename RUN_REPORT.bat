@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo ============================================
echo               XUAT BAO CAO
echo ============================================
set /p TICKER=Nhap ma doanh nghiep: 
if "%TICKER%"=="" exit /b 0
echo.
echo [1] Bao cao Phan tich gia co phieu - Dinh gia - M&A
echo [2] Bao cao Xep hang tin nhiem
echo [3] Xuat ca hai
echo.
set /p CHOICE=Lua chon: 

if "%CHOICE%"=="1" goto :analysis
if "%CHOICE%"=="2" goto :rating
if "%CHOICE%"=="3" goto :both
echo Lua chon khong hop le.
pause
exit /b 1

:analysis
%PYTHON% scripts\export_professional_report.py %TICKER% analysis
goto :done

:rating
%PYTHON% scripts\export_professional_report.py %TICKER% rating
goto :done

:both
%PYTHON% scripts\export_professional_report.py %TICKER% analysis
if errorlevel 1 goto :err
%PYTHON% scripts\export_professional_report.py %TICKER% rating
goto :done

:done
echo.
echo DONE - Bao cao nam trong thu muc reports.
pause
exit /b 0

:err
echo.
echo LOI - Khong xuat duoc bao cao.
pause
exit /b 1
