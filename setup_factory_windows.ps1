# MultiPlatform AI Video Generator — one-command factory setup (Windows)
$ErrorActionPreference = "Stop"
Write-Host "=== MultiPlatform AI Video Factory setup (Windows) ===" -ForegroundColor Cyan

$py = $null
foreach ($c in @("py", "python", "python3")) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
  Write-Error "Python chua cai. Tai https://www.python.org/downloads/ (tick Add to PATH)."
}

Write-Host "[1/5] Tao virtualenv .venv ..."
& $py -m venv .venv
$pip = ".\.venv\Scripts\python.exe"

Write-Host "[2/5] Cai pip packages ..."
& $pip -m pip install --upgrade pip
& $pip -m pip install -r requirements.txt

Write-Host "[3/5] Kiem tra FFmpeg ..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Warning "FFmpeg CHUA co tren PATH. Bat buoc de ghep video."
  Write-Host "  -> https://ffmpeg.org/download.html  hoac: winget install FFmpeg"
} else {
  Write-Host "  FFmpeg OK: $(ffmpeg -version 2>&1 | Select-Object -First 1)"
}

Write-Host "[4/5] Tao file .env ..."
if (-not (Test-Path .env)) {
  if (Test-Path .env.example) {
    Copy-Item .env.example .env
  } else {
    New-Item .env -ItemType File | Out-Null
  }
}
$factoryDefaults = @"

# --- Factory (may tinh nha) ---
PORT=8000
VIDEO_RENDERER=ffmpeg
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=24
VIDEO_MAX_FRAMES=12
OUTPUT_DIR=output
"@
$envText = Get-Content .env -Raw -ErrorAction SilentlyContinue
if ($envText -notmatch "(?m)^PORT=") {
  Add-Content .env $factoryDefaults
  Write-Host "  Da them PORT=8000 va cau hinh factory vao .env"
}
if (-not (Test-Path .env.factory) -and (Test-Path factory.env.example)) {
  Copy-Item factory.env.example .env.factory
}

Write-Host "[5/5] Hoan tat."
Write-Host ""
Write-Host "BUOC TIEP THEO:" -ForegroundColor Green
Write-Host "  1. Mo file .env — dien GROQ_API_KEY va it nhat 1 key anh (OPENAI / GEMINI / OPENROUTER)"
Write-Host "  2. Chay nha may:  .\start_factory.ps1"
Write-Host "  3. Kiem tra:     http://127.0.0.1:8000/health"
Write-Host "  4. (Tuy chon) Cloudflare Tunnel neu app can goi tu 4G:"
Write-Host "       cloudflared tunnel --url http://127.0.0.1:8000"
