@echo off
setlocal
cd /d %~dp0
set /p TICKER=Nhap ma CTCK (vd VDS): 
if "%TICKER%"=="" set TICKER=VDS
C:\Users\HP\.venv\Scripts\python.exe scripts\refresh_securities_capital_ratio.py %TICKER% --years-back 5 --max-peers 10
pause
