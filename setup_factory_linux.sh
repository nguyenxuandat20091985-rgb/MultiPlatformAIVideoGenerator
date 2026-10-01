#!/usr/bin/env bash
# MultiPlatform AI Video Generator — one-command factory setup (Linux/macOS)
set -euo pipefail
echo "=== MultiPlatform AI Video Factory setup (Linux/macOS) ==="

PY=python3
command -v "$PY" >/dev/null || { echo "Can python3"; exit 1; }

echo "[1/5] Tao virtualenv .venv ..."
$PY -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/5] Cai pip packages ..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[3/5] Kiem tra FFmpeg ..."
if ! command -v ffmpeg >/dev/null; then
  echo "WARNING: FFmpeg chua cai. Bat buoc de ghep video."
  echo "  Ubuntu: sudo apt install ffmpeg"
  echo "  macOS:  brew install ffmpeg"
else
  ffmpeg -version | head -1
fi

echo "[4/5] Tao file .env ..."
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
  else
    touch .env
  fi
fi
if ! grep -qE '^PORT=' .env 2>/dev/null; then
  cat >> .env << 'EON'

# --- Factory (may tinh nha) ---
PORT=8000
VIDEO_RENDERER=ffmpeg
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=24
VIDEO_MAX_FRAMES=12
OUTPUT_DIR=output
EON
  echo "  Da them PORT=8000 va cau hinh factory vao .env"
fi
[[ -f factory.env.example && ! -f .env.factory ]] && cp factory.env.example .env.factory || true

echo "[5/5] Hoan tat."
echo ""
echo "BUOC TIEP THEO:"
echo "  1. Mo file .env — dien GROQ_API_KEY + it nhat 1 key anh"
echo "  2. Chay:  ./start_factory.sh"
echo "  3. Kiem tra: http://127.0.0.1:8000/health"
echo "  4. (Tuy chon) cloudflared tunnel --url http://127.0.0.1:8000"
