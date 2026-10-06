@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PYTHON=python"
set "VENV_SELECTED="
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "VENV_SELECTED=%VNSTOCK_VENV_PATH%"
if not defined VENV_SELECTED if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /C:"VNSTOCK_VENV_PATH=" ".env" 2^>nul`) do set "VENV_FROM_FILE=%%B"
  if defined VENV_FROM_FILE if exist "!VENV_FROM_FILE!\Scripts\python.exe" set "VENV_SELECTED=!VENV_FROM_FILE!"
)
if not defined VENV_SELECTED if exist ".venv\Scripts\python.exe" set "VENV_SELECTED=%CD%\.venv"
if defined VENV_SELECTED set "PYTHON=%VENV_SELECTED%\Scripts\python.exe"
set "VNSTOCK_WORKERS=1"
set "VNSTOCK_TICKER_DELAY=1.5"
echo ================================================================
echo V8.74.1 INCREMENTAL / RESUME REFRESH - SPONSOR SAFE
echo Current and known non-current states are preserved; no endless retry loop.
echo Python: %PYTHON%
echo ================================================================
"%PYTHON%" scripts\incremental_resume_refresh.py
if errorlevel 1 goto :err
echo.
echo DONE - Incremental download stage completed.
echo Run RUN_REBUILD_FROM_RAW.bat next.
pause
exit /b 0
:err
echo ERROR - Incremental refresh launcher failed.
pause
exit /b 1
