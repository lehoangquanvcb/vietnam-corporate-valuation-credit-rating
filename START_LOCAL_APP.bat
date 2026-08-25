@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

echo ============================================
echo   VIETNAM CORPORATE INTELLIGENCE - LOCAL
echo ============================================
%PYTHON% -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo LOI: Khong khoi dong duoc Streamlit.
  echo Hay chay SETUP_LOCAL_ENV.bat truoc.
  pause
)
