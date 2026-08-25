@echo off
cd /d "%~dp0"
set REPO=Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence
where gh >nul 2>nul
if errorlevel 1 (
  echo GitHub CLI ^(gh^) chua duoc cai dat. Hay tao repo rong tren github.com roi chay INIT_NEW_GITHUB_REPO.bat.
  pause
  exit /b 1
)
if not exist .git (
  git init
  git branch -M main
  git add .
  git commit -m "Initial V8.0 Multi-Sector Foundation"
)
gh repo create %REPO% --public --source=. --remote=origin --push
pause
