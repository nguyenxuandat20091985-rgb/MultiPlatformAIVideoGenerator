# MultiPlatform AI Video Generator API
# Render / Docker / local — PORT from environment
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    OUTPUT_DIR=output \
    TORCH_HOME=/tmp/torch \
    XDG_CACHE_HOME=/tmp/cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        build-essential \
        libsndfile1 \
        fonts-dejavu-core \
        imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY api.py main.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY publishers/ ./publishers/
COPY assets/ ./assets/

RUN mkdir -p /app/output /tmp/cache /tmp/torch \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app /tmp/cache /tmp/torch

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

CMD ["python", "-c", "import os, uvicorn; uvicorn.run('api:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')))"]
