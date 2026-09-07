@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=python"
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "PYTHON_EXE=%VNSTOCK_VENV_PATH%\Scripts\python.exe"
if exist ".venv\Scripts\python.exe" if not defined VNSTOCK_VENV_PATH set "PYTHON_EXE=.venv\Scripts\python.exe"
set /p TICKER=Nhap ma doanh nghiep can refresh (vi du HPG): 
if "%TICKER%"=="" exit /b 2

echo PACKAGE/REFRESH VERSION: 8.70 STRICT LEVERAGE/CASH-FLOW MODE
echo Python: %PYTHON_EXE%
"%PYTHON_EXE%" scripts\refresh_one_company.py %TICKER%
if errorlevel 1 goto :err
"%PYTHON_EXE%" scripts\coverage_engine.py
if errorlevel 1 goto :err
"%PYTHON_EXE%" scripts\dynamic_peer_engine.py %TICKER%
if errorlevel 1 goto :err
"%PYTHON_EXE%" scripts\sector_benchmark_engine.py %TICKER%
if errorlevel 1 goto :err
"%PYTHON_EXE%" scripts\intelligent_analyst.py %TICKER%
if errorlevel 1 goto :err
"%PYTHON_EXE%" scripts\validate_v8.py
if errorlevel 1 goto :err

echo.
echo DONE - refreshed %TICKER% and rebuilt peer/benchmark/rating layers.
pause
exit /b 0
:err
echo.
echo ERROR - xem log phia tren.
pause
exit /b 1
