@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    set PYTHON_EXE="%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set PYTHON_EXE="%~dp0backend\.venv\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)
echo ============================================================
echo  SIH 26124 - Starting Canonical Backend on http://localhost:8000
echo ============================================================
%PYTHON_EXE% -m uvicorn backend.app.main:app --reload --port 8000 --host 0.0.0.0
pause
