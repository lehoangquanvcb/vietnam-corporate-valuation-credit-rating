@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=C:\Users\HP\.venv\Scripts\python.exe"
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "PYTHON=%VNSTOCK_VENV_PATH%\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo ERROR - Venv Python not found: %PYTHON%
    exit /b 2
)

echo ================================================================
echo V8.74.1 OFFLINE REBUILD - NO VNSTOCK API REQUESTS
echo Python: %PYTHON%
echo Peer crosscheck online refresh is excluded from this workflow.
echo ================================================================

"%PYTHON%" scripts\rebuild_derived_layers.py
if errorlevel 1 goto :err

echo.
echo DONE - V8.74.1 offline rebuild completed.
pause
exit /b 0

:err
echo.
echo ERROR - V8.74.1 offline rebuild stopped. Read log above.
pause
exit /b 1
