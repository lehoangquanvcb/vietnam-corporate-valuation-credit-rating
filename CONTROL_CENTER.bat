@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

:menu
cls
echo =====================================================
echo   VIETNAM CORPORATE VALUATION & CREDIT RATING
echo                  CONTROL CENTER
echo =====================================================
echo.
echo [1] Mo app local
echo [2] Cap nhat nhanh
echo [3] Cap nhat 1 doanh nghiep
echo [4] Full refresh toan thi truong
echo [5] Xuat bao cao
echo [6] Mo thu muc reports
echo [7] Thiet lap moi truong local
echo [0] Thoat
echo.
set /p C=Lua chon: 
if "%C%"=="1" call START_LOCAL_APP.bat
if "%C%"=="2" call RUN_FAST.bat
if "%C%"=="3" call RUN_REFRESH_ONE_COMPANY.bat
if "%C%"=="4" call RUN_FULL_REFRESH.bat
if "%C%"=="5" call RUN_REPORT.bat
if "%C%"=="6" start "" reports
if "%C%"=="7" call SETUP_LOCAL_ENV.bat
if "%C%"=="0" exit /b 0
goto :menu
