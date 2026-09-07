@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PYTHON=python"
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "PYTHON=%VNSTOCK_VENV_PATH%\Scripts\python.exe"
set "VNSTOCK_WORKERS=1"
set "VNSTOCK_TICKER_DELAY=3.0"
echo V8.72 RETRY FAILED TICKERS ONLY
"%PYTHON%" scripts\incremental_resume_refresh.py --only-failed
pause
