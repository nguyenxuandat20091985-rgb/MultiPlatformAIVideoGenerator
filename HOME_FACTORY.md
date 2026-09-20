# Nhà máy tại nhà (miễn phí) — API + Cloudflare Tunnel

App điện thoại chỉ **ra lệnh**. Máy tính nhà anh = **nhà máy** tạo video + đăng bài.

---

## 1. Cài backend trên máy nhà

```bash
git clone https://github.com/nguyenxuandat20091985-rgb/MultiPlatformAIVideoGenerator.git
cd MultiPlatformAIVideoGenerator

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Điền GROQ_API_KEY và TOGETHER_API_KEY vào .env
```

Cài **FFmpeg** (bắt buộc).

Chạy API:

```bash
python api.py
```

Kiểm tra: http://127.0.0.1:8000/health

---

## 2. Public bằng Cloudflare Tunnel (free)

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Copy URL `https://….trycloudflare.com` → dán vào **API Base URL** trên app → Lưu → Kiểm tra.

Máy nhà phải **bật** API + tunnel khi dùng app.

---

## 3. Dùng app

1. Chạy `python api.py` và cloudflared
2. App: URL tunnel → Kiểm tra xanh
3. Topic → nên bật **Bỏ phụ đề** nếu máy yếu → Tạo & Đăng

Chi tiết thêm trong README.md.
