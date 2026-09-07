# SIH 26124 - Start GIS Dashboard Frontend
# Runs from the repository root (urban-dashboard)

$ErrorActionPreference = "Stop"
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $ScriptDir

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' SIH 26124 — GIS Urban Dashboard Frontend [Vite + React]' -ForegroundColor Cyan
Write-Host ' Dashboard URL:    http://localhost:5173' -ForegroundColor Green
Write-Host ' Backend Target:   http://localhost:8000' -ForegroundColor Yellow
Write-Host ' Mode:             Live Backend [VITE_USE_MOCK=false]' -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor Cyan

npm run dev
