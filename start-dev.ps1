# SIH 26124 - Zero-Friction End-to-End Local Development Launcher
# Spawns Backend in Window 1, Frontend in Window 2, and opens Dashboard in Browser

$ErrorActionPreference = "Stop"
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $ScriptDir

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' SIH 26124 — Launching Full Development Environment' -ForegroundColor Cyan
Write-Host ' 1. Backend:  http://localhost:8000 [FastAPI + PostGIS]' -ForegroundColor Green
Write-Host ' 2. Frontend: http://localhost:5173 [React + Google Maps]' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor Cyan

# 1. Launch Backend in new window
Write-Host "[*] Launching Backend server in dedicated terminal..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ScriptDir\start-backend.ps1"

# 2. Launch Frontend in new window
Write-Host "[*] Launching Frontend server in dedicated terminal..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ScriptDir\start-frontend.ps1"

# 3. Wait briefly for servers to bind and open browser
Write-Host "[*] Waiting 3 seconds for services to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host "[*] Opening Urban Intelligence Dashboard in browser..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host '[OK] Dev environment launched successfully! Keep both terminal windows open.' -ForegroundColor Cyan
