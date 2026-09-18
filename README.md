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

## ⚡ Quickstart (chạy trong 5 phút)

```bash
# 1. Clone
git clone https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator.git
cd MultiPlatformAIVideoGenerator

# 2. Virtualenv + cài package
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Cấu hình API
cp .env.example .env
# Điền GROQ_API_KEY + TOGETHER_API_KEY (và keys platform nếu đăng bài)

# 4. FFmpeg bắt buộc
# Ubuntu: sudo apt install ffmpeg

# 5. CLI
python main.py
```

---

## 📱 Mobile App (Flutter) + FastAPI Backend

### Chạy API server

```bash
python api.py
# → http://0.0.0.0:8000  |  Docs: /docs
```

### Tải APK tự động (GitHub Actions) — không cần cài Flutter

1. Vào repo trên GitHub → tab **Actions**
2. Chọn workflow **Build Android APK**
3. Bấm **Run workflow** (có thể nhập `api_base_url`, ví dụ `http://192.168.1.10:8000`)
4. Đợi job **Flutter APK (release)** hoàn tất
5. Kéo xuống **Artifacts** → tải **app-release-apk**
6. Giải nén → file **`app-release.apk`** → cài trên Android

Workflow: `.github/workflows/build_apk.yml`  
- Tự chạy khi push thay đổi trong `mobile_app/`  
- Hoặc chạy tay (`workflow_dispatch`)  
- Artifact giữ **30 ngày**

### Chạy Flutter trên máy

```bash
cd mobile_app
flutter create . --project-name multiplatform_ai_video
flutter pub get
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

### Build APK local (tuỳ chọn)

```bash
cd mobile_app
flutter build apk --release --dart-define=API_BASE_URL=http://YOUR_SERVER_IP:8000
# → build/app/outputs/flutter-apk/app-release.apk
```

Chi tiết: [mobile_app/README.md](mobile_app/README.md)

---

## Tính năng

- Sinh kịch bản (Groq / Llama), ảnh FLUX, TTS, Whisper captions, MoviePy
- Đăng YouTube Shorts / TikTok / Facebook Reels
- CLI + FastAPI + Flutter mobile

## Cấu trúc

```
├── main.py / api.py
├── core/  publishers/
├── mobile_app/          # Flutter
├── .github/workflows/
│   ├── ci.yml
│   └── build_apk.yml    # Build + upload APK artifact
└── output/
```

## License

MIT
