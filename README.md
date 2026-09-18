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
# Windows:  .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# 3. Cấu hình API (tối thiểu 2 key để tạo video)
cp .env.example .env
# Mở .env, điền:
#   GROQ_API_KEY=...          → https://console.groq.com
#   TOGETHER_API_KEY=...      → https://api.together.xyz
# (Tuỳ chọn đăng bài: YouTube / TikTok / Facebook – xem bên dưới)

# 4. Cài FFmpeg (bắt buộc)
#   Ubuntu: sudo apt install ffmpeg
#   macOS:  brew install ffmpeg
#   Windows: tải từ ffmpeg.org và thêm vào PATH

# 5. Chạy!
python main.py
# hoặc:
python main.py run --folder demo --topic "5 productivity tips" --style educational
```

**Tạo + đăng một lệnh:**
```bash
python main.py run \
  --folder productivity \
  --topic "5 tips to stay productive" \
  --title "5 Productivity Tips #Shorts" \
  --platforms youtube,facebook \
  --tags "productivity,tips,ai"
```

**Chỉ tạo video / chỉ đăng:**
```bash
python main.py generate --folder my_video --topic "Your topic here"
python main.py publish --video output/my_video/final_video_with_captions.mp4 --title "My Short" --platforms youtube
python main.py status   # xem platform nào đã cấu hình
```

---

## Tính năng

- Sinh kịch bản (Groq / Llama)
- Sinh ảnh dọc 9:16 (Together AI FLUX)
- TTS (Kokoro → fallback Edge-TTS)
- Phụ đề Whisper + burn-in
- Ghép video MoviePy
- Đăng đa nền tảng qua `publishers/` (dễ thêm mạng mới)

---

## Cấu trúc thư mục

```
MultiPlatformAIVideoGenerator/
├── main.py                  # CLI + interactive
├── requirements.txt
├── .env.example
├── config/settings.py       # Load biến môi trường
├── core/                    # Pipeline tạo video
│   ├── script_generator.py
│   ├── image_prompt_generator.py
│   ├── image_generator.py
│   ├── audio_generator.py
│   ├── caption_generator.py
│   ├── video_composer.py
│   └── caption_overlay.py
├── publishers/              # Đăng tải
│   ├── base.py
│   ├── youtube.py
│   ├── tiktok.py
│   ├── facebook.py
│   └── registry.py
├── .github/workflows/ci.yml
└── output/                  # Kết quả (gitignore)
```

---

## Cấu hình API chi tiết

### 1. Core AI (bắt buộc tạo video)

| Biến | Lấy ở đâu |
|------|-----------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |
| `TOGETHER_API_KEY` | [api.together.xyz](https://api.together.xyz) → API Keys |

```env
GROQ_API_KEY=gsk_xxxxxxxx
TOGETHER_API_KEY=xxxxxxxx
```

### 2. YouTube Shorts

1. [Google Cloud Console](https://console.cloud.google.com/) → tạo project
2. Enable **YouTube Data API v3**
3. Credentials → OAuth client ID → **Desktop app** → tải JSON
4. Đổi tên thành `client_secrets.json`, đặt ở thư mục gốc project
5. Lần chạy đầu mở trình duyệt cấp quyền → lưu `token.json`

```env
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
YOUTUBE_TOKEN_FILE=token.json
YOUTUBE_PRIVACY_STATUS=public
```

> Video dọc ≤ 60s + `#Shorts` trong title/description → YouTube phân loại Short.

### 3. TikTok Content Posting API

1. [developers.tiktok.com](https://developers.tiktok.com) → tạo App
2. Thêm **Content Posting API**, scope: `video.upload`, `video.publish`
3. OAuth lấy `access_token` của creator

```env
TIKTOK_ACCESS_TOKEN=act.xxxxxxxx
TIKTOK_PRIVACY_LEVEL=PUBLIC_TO_EVERYONE
# Dev: dùng SELF_ONLY nếu chưa audit
```

### 4. Facebook Reels (Fanpage)

1. [developers.facebook.com](https://developers.facebook.com) → tạo App
2. Lấy **Page ID** + **Page Access Token** dài hạn  
   Quyền: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`

```env
FACEBOOK_PAGE_ID=123456789012345
FACEBOOK_PAGE_ACCESS_TOKEN=EAABsbCS1iHgBO...
FACEBOOK_API_VERSION=v21.0
```

### Kiểm tra

```bash
python main.py status
```

---

## Yêu cầu hệ thống

- Python **3.11+**
- **FFmpeg** trên PATH (bắt buộc)
- ImageMagick (khuyến nghị, đặc biệt Windows cho TextClip)

---

## Mở rộng nền tảng mới

1. Tạo `publishers/instagram.py` kế thừa `BasePublisher`
2. Implement `is_configured()` và `publish(...)`
3. Đăng ký trong `publishers/registry.py`:

```python
PUBLISHERS = {
    ...
    "instagram": InstagramPublisher,
}
```

4. Thêm biến vào `.env.example` + `config/settings.py`

---

## Lưu ý API

| Nền tảng | Lưu ý |
|----------|--------|
| YouTube | Quota riêng; public cần project verified |
| TikTok | ~6 init/phút/token; audit app để public |
| Facebook | Chỉ đăng **Page**; video 9:16, ~3–90s |

---

## License

MIT
