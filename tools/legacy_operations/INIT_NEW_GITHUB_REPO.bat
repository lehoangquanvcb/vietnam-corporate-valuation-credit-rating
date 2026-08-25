@echo off
cd /d "%~dp0"
echo ==========================================================
echo V8 NEW REPOSITORY INITIALIZER
echo Suggested repo: Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence
echo ==========================================================
if exist .git (
  echo Thu muc nay da co .git. Khong khoi tao lai.
  pause
  exit /b 0
)
git init
git branch -M main
git add .
git commit -m "Initial V8.0 Multi-Sector Foundation"
echo.
echo Buoc tiep theo: tao repo RONG tren GitHub, sau do chay:
echo git remote add origin https://github.com/YOUR_USERNAME/Vietnam_Corporate_Valuation_MA_Credit_Rating_Intelligence.git
echo git push -u origin main
pause
