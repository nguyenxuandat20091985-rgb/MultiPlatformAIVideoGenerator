# Deploy API lên Render (Free) — không cần máy nhà

URL sau khi deploy dạng: `https://<tên-service>.onrender.com`

---

## 0. Chuẩn bị

- Tài khoản https://render.com (đăng nhập bằng GitHub cho nhanh)
- Repo: https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator
- Key: `GROQ_API_KEY`, `TOGETHER_API_KEY`

---

## 1. Tạo Web Service trên Render

1. Vào https://dashboard.render.com
2. **New +** → **Web Service**
3. Connect GitHub → chọn repo **MultiPlatformAIVideoGenerator**
4. Cấu hình:

| Ô | Giá trị |
|---|--------|
| **Name** | `multiplatform-ai-video-api` |
| **Region** | Singapore (nếu có) |
| **Runtime** | **Docker** |
| **Dockerfile Path** | `./Dockerfile` |
| **Branch** | `main` |
| **Instance type** | **Free** |

5. **Environment** → Add:

| Key | Value |
|-----|--------|
| `GROQ_API_KEY` | khóa Groq |
| `TOGETHER_API_KEY` | khóa Together |
| `OUTPUT_DIR` | `output` |

6. **Create Web Service**

Build lần đầu có thể **10–20 phút** (torch + ffmpeg).

---

## 2. Kiểm tra

```text
https://<tên-service>.onrender.com/health
https://<tên-service>.onrender.com/docs
```

---

## 3. App di động

API Base URL = `https://<tên-service>.onrender.com` (không `/` cuối) → Lưu → Kiểm tra.

---

## 4. Lưu ý Free

- Ngủ sau **15 phút** không traffic → lần sau cold start 30–60s
- RAM ~512MB: job Whisper có thể nặng
- Disk tạm: video có thể mất khi restart
