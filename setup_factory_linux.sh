#!/usr/bin/env bash
set -euo pipefail
echo "=== MultiPlatform AI Video Factory setup ==="
python3 -m venv .venv || true
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
command -v ffmpeg >/dev/null || echo "WARNING: install FFmpeg and ensure it is on PATH"
command -v node >/dev/null || echo "INFO: Node.js 20+ is optional for OpenCut/Remotion"
cp -n factory.env.example .env.factory 2>/dev/null || true
echo "Setup complete. Copy .env.factory to .env and add your provider keys."
echo "Default renderer: FFmpeg. Optional local ComfyUI: http://127.0.0.1:8188"
