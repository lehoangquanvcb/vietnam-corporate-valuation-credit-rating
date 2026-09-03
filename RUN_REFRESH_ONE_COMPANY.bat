@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ------------------------------------------------------------
rem Select Python for Vnstock Sponsor in this order:
rem   1) Windows environment variable VNSTOCK_VENV_PATH
rem   2) Local .env VNSTOCK_VENV_PATH
rem   3) Project .venv
rem   4) System python
rem ------------------------------------------------------------
set "PYTHON=python"
set "VENV_SELECTED="

rem 1) Windows/user environment variable (setx VNSTOCK_VENV_PATH ...)
if defined VNSTOCK_VENV_PATH (
  if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" (
    set "VENV_SELECTED=%VNSTOCK_VENV_PATH%"
  )
)

rem 2) .env overrides only when no valid Windows env path was found
if not defined VENV_SELECTED if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"VNSTOCK_VENV_PATH=" ".env" 2^>nul`) do (
    set "VENV_FROM_FILE=%%B"
  )
  if defined VENV_FROM_FILE if exist "!VENV_FROM_FILE!\Scripts\python.exe" set "VENV_SELECTED=!VENV_FROM_FILE!"
)

rem 3) project-local venv
if not defined VENV_SELECTED if exist ".venv\Scripts\python.exe" set "VENV_SELECTED=%CD%\.venv"

if defined VENV_SELECTED set "PYTHON=%VENV_SELECTED%\Scripts\python.exe"

echo ============================================
echo   CAP NHAT 1 DOANH NGHIEP - VNSTOCK SPONSOR
echo ============================================
echo Python: %PYTHON%
set /p TICKER=Nhap ma doanh nghiep (VD: VCB, SSI, HPG): 
if "%TICKER%"=="" goto :end

"%PYTHON%" scripts\refresh_one_company.py %TICKER%
if errorlevel 1 goto :err

echo Cap nhat dynamic peer + benchmark + analyst...
"%PYTHON%" scripts\dynamic_peer_engine.py
if errorlevel 1 goto :err
"%PYTHON%" scripts\sector_benchmark_engine.py
if errorlevel 1 goto :err
"%PYTHON%" scripts\intelligent_analyst.py
if errorlevel 1 goto :err

echo.
echo DONE - %TICKER%
pause
exit /b 0
:err
echo.
echo LOI - xem thong bao phia tren. Hay chay RUN_DIAGNOSE_VNSTOCK.bat.
pause
exit /b 1
:end
