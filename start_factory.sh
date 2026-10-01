#!/usr/bin/env bash
# Start local video factory API (Linux/macOS)
set -euo pipefail
if [[ ! -f .venv/bin/python ]]; then
  echo "Chua setup. Chay truoc: bash setup_factory_linux.sh"
  exit 1
fi
if [[ ! -f .env ]]; then
  echo "WARNING: Thieu .env — copy tu .env.example va dien API keys."
fi
export PORT="${PORT:-8000}"
echo "Starting factory on http://0.0.0.0:${PORT} ..."
echo "Health: http://127.0.0.1:${PORT}/health"
echo "Docs:   http://127.0.0.1:${PORT}/docs"
exec .venv/bin/python api.py
