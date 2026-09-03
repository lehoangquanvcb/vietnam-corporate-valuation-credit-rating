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

echo ===========================================================
echo RECOVER FULL-MARKET BRONZE FROM EXISTING RAW FILES
echo No Vnstock fundamentals re-download required
echo ===========================================================
echo Python: %PYTHON%

echo.
echo ^>^>^> Restore current full Vnstock universe ^(listing only^)
"%PYTHON%" scripts\discover_listed_universe.py
if errorlevel 1 goto :err
"%PYTHON%" scripts\industry_classifier.py
if errorlevel 1 echo WARNING - industry classifier incomplete; continuing with listing metadata.

echo.
echo ^>^>^> Rebuild multisector Bronze from existing data\raw
"%PYTHON%" scripts\rebuild_multisector_from_raw.py
if errorlevel 1 goto :err

for %%S in (coverage_engine.py dynamic_peer_engine.py sector_benchmark_engine.py intelligent_analyst.py validate_v8.py) do (
  echo.
  echo ^>^>^> scripts\%%S
  "%PYTHON%" scripts\%%S
  if errorlevel 1 goto :err
)

echo.
echo DONE - Full-market recovery and derived layers completed.
pause
exit /b 0
:err
echo.
echo ERROR - Recovery stopped. Read the terminal log above.
pause
exit /b 1
