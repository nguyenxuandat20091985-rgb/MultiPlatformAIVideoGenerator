# MultiPlatform AI Video Generator & Auto-Publisher

AI tạo video dọc (Shorts / Reels / TikTok) → **tự động đăng** lên YouTube, TikTok, Facebook.

## Image generation failover

The image step supports automatic provider failover:

1. **OpenRouter** — uses `openai/gpt-image-2`.
2. **Gemini** — direct Google Gemini image API using `gemini-3.1-flash-image`.

Set `IMAGE_PROVIDER_ORDER=openrouter,gemini`. When a provider returns an API/auth/credit error, it is disabled for the rest of that video job and the next configured provider is used automatically. This prevents an unavailable provider from making all remaining scenes fail.

Required for generation:
- `GROQ_API_KEY`
- At least one image key: `OPENROUTER_API_KEY` or `GEMINI_API_KEY`

Gemini's current image API supports 9:16 output and the 3.1 Flash Image model. OpenRouter's current image API also supports centralized routing and image generation. 

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
