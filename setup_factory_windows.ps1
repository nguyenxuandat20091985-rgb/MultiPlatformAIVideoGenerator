$ErrorActionPreference = "Stop"
Write-Host "=== MultiPlatform AI Video Factory setup ==="
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Warning "FFmpeg is not on PATH. Install FFmpeg before rendering."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Host "Node.js 20+ is optional for OpenCut/Remotion."
}
if (-not (Test-Path .env.factory)) {
  Copy-Item factory.env.example .env.factory
}
Write-Host "Setup complete. Copy .env.factory to .env and add provider keys."
