# MultiPlatform AI Video Generator & Auto-Publisher

AI tạo video dọc (Shorts / Reels / TikTok) → **tự động đăng** lên YouTube, TikTok, Facebook.

## Image generation failover

The image pipeline uses ordered provider/key failover:

1. **OpenAI direct** — `OPENAI_API_KEY` → `OPENAI_API_KEY_4`, using `gpt-image-2`.
2. **Gemini** — `GEMINI_API_KEY` → `GEMINI_API_KEY_4`.
3. **OpenRouter** — `OPENROUTER_API_KEY` → `OPENROUTER_API_KEY_4`.

Default order is `openai,gemini,openrouter`. OpenAI image generation uses the official Images API and returns base64 image data; the app normalizes the result to PNG. OpenAI's image API supports portrait output such as `1024x1536`; the prompt also explicitly requests vertical 9:16 composition. citeturn3search1turn2search0

A permanent HTTP authentication/credit/configuration failure (401/402/403/404) disables that key for the remainder of the current video job. Other configured keys/providers are then tried automatically. API keys are never printed in errors or health responses.\n\nIf every remote image provider is unavailable (for example, all accounts have exhausted credits), the pipeline now creates a deterministic local visual fallback with Pillow for each missing frame instead of failing the entire video job. The job continues to audio, composition, captions, and publishing. The image folder also receives `image_generation_report.json` so the fallback usage is auditable. These fallback frames are not AI-generated; they are a resilience mechanism.

Required for generation:
- `GROQ_API_KEY`
- At least one image key: `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY`

## Quickstart

```bash
cp .env.example .env
# Fill GROQ_API_KEY and one or both image-provider keys
python main.py
```

## API

```bash
python api.py
# http://0.0.0.0:8000  |  Docs: /docs
```

## Mobile App

The existing Flutter mobile app calls the FastAPI backend and can continue using the same API endpoint.

## Features

- Script generation with Groq
- Rich image prompts with Groq
- Image generation with OpenAI + Gemini + OpenRouter failover and local fallback
- TTS + Whisper captions + MoviePy
- YouTube Shorts / TikTok / Facebook Reels publishing
- FastAPI + Flutter mobile app

## Remote video worker

For video jobs that exceed the RAM available on a small web instance, the API can
delegate the heavy pipeline to a separate Worker. Render remains the public API
and job-status endpoint; the Worker runs FFmpeg/AI processing and exposes the
finished video through its own `/media` URL.

Architecture:

```
App → Render API → Video Worker (large RAM) → /media video
                  ↑ job status/callback
```

Set these variables on Render:
- `VIDEO_WORKER_URL`: public HTTPS URL of the Worker.
- `VIDEO_WORKER_TOKEN`: shared secret between Render and Worker.
- `PUBLIC_BASE_URL`: public HTTPS URL of the Render API.
- `WORKER_MODE=0`.

Set these variables on the Worker:
- `WORKER_MODE=1`
- `WORKER_TOKEN`: the same value as Render's `VIDEO_WORKER_TOKEN`.
- `PUBLIC_BASE_URL`: public HTTPS URL of the Worker.
- Copy the AI/provider environment variables required by the existing pipeline.

The Worker can use the same Docker image with the `worker.py` entrypoint.
`docker-compose.worker.yml` is included for a VM deployment.

The Render Free web service remains limited to 512 MB RAM, so this separation is
designed to keep FFmpeg/AI memory usage away from the API process. Render's
current compute documentation lists 512 MB for the Free web service and paid
plans for larger worker instances. 

## License

MIT
