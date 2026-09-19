# MultiPlatform AI Video Generator & Auto-Publisher

AI tạo video dọc (Shorts / Reels / TikTok) → **tự động đăng** lên YouTube, TikTok, Facebook.

## Image generation failover

The image step uses ordered provider/key failover:

1. **Gemini** — direct Google Gemini image API using `gemini-3.1-flash-image`.
2. **OpenRouter** — image generation through `/api/v1/images` using the configured image model.

Set `IMAGE_PROVIDER_ORDER=gemini,openrouter` (the default). Each provider supports up to four keys:
`GEMINI_API_KEY` through `GEMINI_API_KEY_4`, and
`OPENROUTER_API_KEY` through `OPENROUTER_API_KEY_4`.

A permanent HTTP authentication/credit/configuration failure (401/402/403/404) disables only that key for the remainder of the current video job. Other configured keys/providers are then tried automatically. Transient failures remain eligible for later scenes.

The application never prints API keys in error messages. Health diagnostics expose only provider configuration state and key counts.

Required for generation:
- `GROQ_API_KEY`
- At least one image key in either the Gemini or OpenRouter key slots

Important: failover cannot make an invalid/suspended key or an account with no image-generation credits usable. Those provider accounts still need valid access/credits.

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
- Image generation with OpenRouter + Gemini failover
- TTS + Whisper captions + MoviePy
- YouTube Shorts / TikTok / Facebook Reels publishing
- FastAPI + Flutter mobile app

## License

MIT
