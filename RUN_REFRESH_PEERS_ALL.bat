@echo off
setlocal
cd /d "%~dp0"
set "PEER_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PEER_PYTHON=%CD%\.venv\Scripts\python.exe"
if exist "%USERPROFILE%\.venv\Scripts\python.exe" set "PEER_PYTHON=%USERPROFILE%\.venv\Scripts\python.exe"
if defined VNSTOCK_VENV_PATH if exist "%VNSTOCK_VENV_PATH%\Scripts\python.exe" set "PEER_PYTHON=%VNSTOCK_VENV_PATH%\Scripts\python.exe"
echo V8.123 - AUTO PEERS FOR ALL TICKERS
echo Python: %PEER_PYTHON%
"%PEER_PYTHON%" scripts\refresh_market_peers.py %*
set "PEER_EXIT=%ERRORLEVEL%"
if not "%PEER_EXIT%"=="0" echo Some steps did not finish. Read the error above and run the same command to resume.
pause
exit /b %PEER_EXIT%
