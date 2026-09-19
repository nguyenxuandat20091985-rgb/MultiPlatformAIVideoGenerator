# MultiPlatform AI Video Generator & Auto-Publisher

AI tạo video dọc (Shorts / Reels / TikTok) → **tự động đăng** lên YouTube, TikTok, Facebook.

## Image generation failover

The image pipeline uses ordered provider/key failover:

1. **OpenAI direct** — `OPENAI_API_KEY` → `OPENAI_API_KEY_4`, using `gpt-image-2`.
2. **Gemini** — `GEMINI_API_KEY` → `GEMINI_API_KEY_4`.
3. **OpenRouter** — `OPENROUTER_API_KEY` → `OPENROUTER_API_KEY_4`.

Default order is `openai,gemini,openrouter`. OpenAI image generation uses the official Images API and returns base64 image data; the app normalizes the result to PNG. OpenAI's image API supports portrait output such as `1024x1536`; the prompt also explicitly requests vertical 9:16 composition. citeturn3search1turn2search0

A permanent HTTP authentication/credit/configuration failure (401/402/403/404) disables that key for the remainder of the current video job. Other configured keys/providers are then tried automatically. API keys are never printed in errors or health responses.

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
- Image generation with OpenRouter + Gemini failover
- TTS + Whisper captions + MoviePy
- YouTube Shorts / TikTok / Facebook Reels publishing
- FastAPI + Flutter mobile app

## License

MIT
