@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "PYTHON=%VNSTOCK_VENV_PATH%\Scripts\python.exe"
echo ================================================================
echo V8.72 OFFLINE REBUILD - NO VNSTOCK API REQUESTS
echo ================================================================
"%PYTHON%" scripts\rebuild_derived_layers.py
if errorlevel 1 goto :err
echo DONE - Offline rebuild completed.
pause
exit /b 0
:err
echo ERROR - Offline rebuild stopped. Read log above.
pause
exit /b 1
