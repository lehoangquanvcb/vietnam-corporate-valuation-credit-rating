@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo     THIET LAP MOI TRUONG LOCAL
echo ============================================
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if exist requirements.local.txt (
    pip install -r requirements.local.txt
) else (
    pip install -r requirements.txt
)
echo.
echo HOAN TAT.
pause
