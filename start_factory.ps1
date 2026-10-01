# Start local video factory API (Windows)
$ErrorActionPreference = "Stop"
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  Write-Host "Chua setup. Chay truoc: .\setup_factory_windows.ps1" -ForegroundColor Yellow
  exit 1
}
if (-not (Test-Path .env)) {
  Write-Warning "Thieu .env — copy tu .env.example va dien API keys."
}
if (-not $env:PORT) { $env:PORT = "8000" }
Write-Host "Starting factory on http://0.0.0.0:$($env:PORT) ..." -ForegroundColor Cyan
Write-Host "Health: http://127.0.0.1:$($env:PORT)/health"
Write-Host "Docs:   http://127.0.0.1:$($env:PORT)/docs"
& .\.venv\Scripts\python.exe api.py
