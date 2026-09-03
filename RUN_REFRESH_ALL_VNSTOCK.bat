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

echo ===========================================================
echo  FULL VNSTOCK SPONSOR REFRESH - TOAN BO THI TRUONG
echo ===========================================================
echo Python: %PYTHON%
echo Sponsor source: vnstock_data ^(local Bronze credential; key never printed^)
echo Vnstock Reference ^> ALL listed tickers ^> BANK + SECURITIES + CORPORATE
echo ^> full raw fundamentals ^> normalized Bronze ^> dynamic peer ^> benchmark ^> analyst
echo.
"%PYTHON%" scripts\refresh_all_vnstock.py
if errorlevel 1 goto :err

echo.
echo DONE - Full-market Vnstock Sponsor refresh completed.
pause
exit /b 0
:err
echo.
echo ERROR - Refresh stopped. Read the terminal log above.
echo Tip: run RUN_DIAGNOSE_VNSTOCK.bat first.
pause
exit /b 1
