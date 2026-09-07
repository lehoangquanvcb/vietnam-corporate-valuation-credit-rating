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
set /p TICKER=Nhap ma doanh nghiep can refresh peer (vi du HPG): 
if "%TICKER%"=="" exit /b 1
set "VNSTOCK_WORKERS=1"
set "VNSTOCK_TICKER_DELAY=3.0"
echo ================================================================
echo V8.72.1 TARGET PEER REFRESH - BRONZE SAFE
echo Target: %TICKER%
echo Python: %PYTHON%
echo ================================================================
"%PYTHON%" scripts\refresh_target_peers.py %TICKER%
if errorlevel 1 goto :err
echo.
echo DONE - peer data / peer map / benchmark refreshed for %TICKER%.
pause
exit /b 0
:err
echo ERROR - target peer refresh failed. Read terminal log above.
pause
exit /b 1
