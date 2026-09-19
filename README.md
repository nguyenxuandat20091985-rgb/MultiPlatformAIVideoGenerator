# MultiPlatform AI Video Generator & Auto-Publisher

AI tạo video dọc (Shorts / Reels / TikTok) → **tự động đăng** lên YouTube, TikTok, Facebook.

| Nền tảng | API | Trạng thái |
|----------|-----|------------|
| **YouTube Shorts** | YouTube Data API v3 | ✅ |
| **TikTok** | Content Posting API | ✅ |
| **Facebook Reels** | Graph API (Page) | ✅ |
| Instagram / LinkedIn / X… | Extensible | 🔧 Sẵn cấu trúc |

Dựa trên [GabrielLaxy/TikTokAIVideoGenerator](https://github.com/GabrielLaxy/TikTokAIVideoGenerator), tái cấu trúc + mở rộng multi-platform.

---

## ⚡ Quickstart

```bash
git clone https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator.git
cd MultiPlatformAIVideoGenerator

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Cấu hình API
cp .env.example .env
# Điền GROQ_API_KEY + OPENROUTER_API_KEY

# FFmpeg bắt buộc
# Ubuntu: sudo apt install ffmpeg

python main.py
```

## 📱 Mobile App (Flutter) + FastAPI Backend

### Chạy API server

```bash
python api.py
# → http://0.0.0.0:8000  |  Docs: /docs
```

### Tải APK tự động (GitHub Actions)

1. Vào repo trên GitHub → tab **Actions**
2. Chọn workflow **Build Android APK**
3. Bấm **Run workflow** (có thể nhập `api_base_url`)
4. Đợi job **Flutter APK (release)** hoàn tất
5. Tải artifact **app-release-apk** và cài `app-release.apk`

Workflow: `.github/workflows/build_apk.yml`

## Tính năng

- Sinh kịch bản (Groq / Llama), sinh prompt ảnh (Groq / Llama)
- Sinh ảnh dọc 9:16 qua **OpenRouter Images API**
- TTS, Whisper captions, MoviePy
- Đăng YouTube Shorts / TikTok / Facebook Reels
- CLI + FastAPI + Flutter mobile

## Cấu trúc

```
├── main.py / api.py
├── config/  core/  publishers/
├── mobile_app/
├── .github/workflows/
│   ├── ci.yml
│   └── build_apk.yml
└── output/
```

## License

MIT
