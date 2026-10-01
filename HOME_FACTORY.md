# Nhà máy video trên máy tính (khuyến nghị)

App điện thoại chỉ **ra lệnh**. Máy tính = **nhà máy** (AI + FFmpeg + đăng bài).

---

## Windows (PowerShell)

```powershell
git clone https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator.git
cd MultiPlatformAIVideoGenerator

# 1) Cài môi trường (một lần)
.\setup_factory_windows.ps1

# 2) Mở .env — điền tối thiểu:
#    GROQ_API_KEY=...
#    OPENAI_API_KEY=...   (hoặc GEMINI_API_KEY / OPENROUTER_API_KEY)

# 3) Bật nhà máy
.\start_factory.ps1
```

Kiểm tra trình duyệt: http://127.0.0.1:8000/health

### FFmpeg (bắt buộc)

```powershell
winget install FFmpeg
# hoặc tải https://ffmpeg.org và thêm vào PATH
```

---

## Linux / macOS

```bash
git clone https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator.git
cd MultiPlatformAIVideoGenerator

bash setup_factory_linux.sh
# Sửa .env (GROQ_API_KEY + key ảnh)
./start_factory.sh
```

```bash
# FFmpeg
sudo apt install ffmpeg    # Ubuntu
brew install ffmpeg        # macOS
```

---

## Kết nối app điện thoại

### Cùng Wi‑Fi (đơn giản)

1. Xem IP máy tính:
   - Windows: `ipconfig` → IPv4 (vd `192.168.1.20`)
   - Linux/macOS: `ip a` hoặc `ifconfig`
2. App → **API Base URL** = `http://192.168.1.20:8000`
3. **Lưu** → **Kiểm tra** (xanh)

Firewall Windows: cho phép Python/port 8000 nếu bị chặn.

### 4G / ngoài nhà (Cloudflare Tunnel free)

Terminal **thứ 2** (API vẫn chạy):

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Copy URL `https://….trycloudflare.com` → dán vào app.

---

## Tạo video CLI (không cần app)

```bash
# Windows: .\.venv\Scripts\activate
source .venv/bin/activate

python main.py run --folder demo --topic "3 tips for better sleep" --style educational
```

---

## Biến môi trường quan trọng

| Biến | Mặc định | Ý nghĩa |
|------|----------|--------|
| `PORT` | `8000` | Cổng API |
| `GROQ_API_KEY` | — | Bắt buộc (kịch bản) |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | — | Ít nhất 1 key ảnh |
| `VIDEO_RENDERER` | `ffmpeg` | Engine ghép video |
| `VIDEO_MAX_FRAMES` | `12` | Số khung tối đa |

File mẫu: `.env.example`, `factory.env.example`.

---

## Lưu ý

- Máy **bật** + `start_factory` đang chạy thì app mới tạo được video.
- Render Free (~512MB) **không** đủ; máy tính mới là nhà máy chính.
- Đăng YouTube/TikTok/Facebook: thêm token trong `.env` (xem `.env.example`).
