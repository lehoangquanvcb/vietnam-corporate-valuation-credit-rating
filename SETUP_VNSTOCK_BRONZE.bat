@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_VNSTOCK_BRONZE.ps1"
if errorlevel 1 (
  echo.
  echo ERROR - Bronze credential setup failed.
  pause
  exit /b 1
)
echo.
pause
