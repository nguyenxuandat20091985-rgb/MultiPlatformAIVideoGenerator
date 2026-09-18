---
title: AI Video Generator API
emoji: 🎥
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# AI Video Generator API (Hugging Face Space)

FastAPI backend for **MultiPlatform AI Video Generator**.

Public URL after deploy:

```text
https://<your-username>-<space-name>.hf.space
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + configured platforms |
| POST | `/api/v1/generate` | Start generation job |
| GET | `/api/v1/jobs/{id}` | Poll progress |
| GET | `/api/v1/jobs/{id}/video` | Download video |
| GET | `/media/...` | Static files under `output/` |
| POST | `/api/v1/publish` | Publish existing video |

Interactive docs: `/docs`

## Secrets (Space → Settings → Variables and secrets)

Required for generation:

- `GROQ_API_KEY`
- `TOGETHER_API_KEY`

Optional publish:

- `TIKTOK_ACCESS_TOKEN`
- `FACEBOOK_PAGE_ID`
- `FACEBOOK_PAGE_ACCESS_TOKEN`

## Mobile app

In the Flutter app, set **API Base URL** to:

```text
https://<your-username>-<space-name>.hf.space
```

(no trailing slash)

## Local Docker test

```bash
docker build -t ai-video-api .
docker run --rm -p 7860:7860 \
  -e GROQ_API_KEY=... \
  -e TOGETHER_API_KEY=... \
  ai-video-api
```
