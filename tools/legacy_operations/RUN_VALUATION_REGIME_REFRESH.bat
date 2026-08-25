@echo off
cd /d "%~dp0"
echo [1/2] Cap nhat benchmark P/E P/B nganh/thi truong tu Vnstock LOCAL...
python scripts\refresh_vnstock_peer_crosscheck.py
if errorlevel 1 goto :err
echo [2/2] Cap nhat Intelligent Analyst...
python scripts\intelligent_analyst.py
if errorlevel 1 goto :err
echo DONE.
pause
exit /b 0
:err
echo ERROR - xem thong bao phia tren.
pause
exit /b 1
