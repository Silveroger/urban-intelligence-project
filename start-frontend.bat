@echo off
cd /d "%~dp0"
echo ============================================================
echo  SIH 26124 - Starting GIS Frontend on http://localhost:5173
echo ============================================================
npm run dev
pause
