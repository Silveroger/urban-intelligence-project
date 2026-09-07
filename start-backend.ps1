# SIH 26124 - Start Canonical FastAPI Backend
# Runs from the repository root (urban-dashboard)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# Locate virtualenv python
$PythonPath = $null
if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonPath = "$ScriptDir\.venv\Scripts\python.exe"
} elseif (Test-Path "$ScriptDir\backend\.venv\Scripts\python.exe") {
    $PythonPath = "$ScriptDir\backend\.venv\Scripts\python.exe"
} else {
    $PythonPath = "python"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SIH 26124 — Urban Intelligence Platform Canonical Backend" -ForegroundColor Cyan
Write-Host " Runtime: $PythonPath" -ForegroundColor Gray
Write-Host " Root Directory: $ScriptDir" -ForegroundColor Gray
Write-Host " API Documentation: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host " Health Check:     http://localhost:8000/health" -ForegroundColor Green
Write-Host " Database Health:  http://localhost:8000/health/database" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

& $PythonPath -m uvicorn backend.app.main:app --reload --port 8000 --host 0.0.0.0
