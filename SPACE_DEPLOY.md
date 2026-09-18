# Deploy backend lên Hugging Face Spaces (Docker)

Mục tiêu: API public qua Internet (`https://….hf.space`) để app điện thoại gọi được mọi nơi (4G/5G/Wi‑Fi), không cần bật máy tính ở nhà.

---

## 1. Chuẩn bị trên Hugging Face

1. Đăng nhập https://huggingface.co
2. **New Space**
   - **Space name**: ví dụ `ai-video-generator-api`
   - **SDK**: **Docker**
   - **Hardware**: CPU basic (nâng cấp nếu cần)
   - Visibility: Public hoặc Private
3. **Settings → Variables and secrets → New secret**:
   - `GROQ_API_KEY`
   - `TOGETHER_API_KEY`
   - (tuỳ chọn) `TIKTOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`

---

## 2. Push code lên Space bằng Git

### Cách A — Clone Space rồi copy file

```bash
pip install -U huggingface_hub
huggingface-cli login

git clone https://huggingface.co/spaces/USER/SPACE
cd SPACE

# Từ repo MultiPlatformAIVideoGenerator
cp ../MultiPlatformAIVideoGenerator/Dockerfile .
cp ../MultiPlatformAIVideoGenerator/.dockerignore .
cp ../MultiPlatformAIVideoGenerator/api.py .
cp ../MultiPlatformAIVideoGenerator/main.py .
cp ../MultiPlatformAIVideoGenerator/requirements.txt .
cp -r ../MultiPlatformAIVideoGenerator/config .
cp -r ../MultiPlatformAIVideoGenerator/core .
cp -r ../MultiPlatformAIVideoGenerator/publishers .
cp -r ../MultiPlatformAIVideoGenerator/assets .
cp ../MultiPlatformAIVideoGenerator/README.hf.md README.md

git add .
git commit -m "Deploy AI Video Generator API (Docker)"
git push
```

### Cách B — Remote HF từ repo hiện có

```bash
cd MultiPlatformAIVideoGenerator
git checkout -b hf-space
cp README.hf.md README.md
git add Dockerfile .dockerignore README.md api.py main.py requirements.txt config core publishers assets
git commit -m "HF Space Docker deploy"
git remote add hf https://huggingface.co/spaces/USER/SPACE
git push hf hf-space:main
```

Token write: https://huggingface.co/settings/tokens

---

## 3. Chờ build & lấy URL

```text
https://USER-SPACE.hf.space
```

```bash
curl https://USER-SPACE.hf.space/health
```

Docs: `https://USER-SPACE.hf.space/docs`

---

## 4. App di động

1. Ô **API Base URL** → `https://USER-SPACE.hf.space`
2. **Lưu URL** → **Kiểm tra**
3. Tạo video

---

## 5. Lưu ý

| Chủ đề | Chi tiết |
|--------|----------|
| Port | **7860** |
| Secrets | Không commit `.env` |
| Job dài | Free CPU có thể chậm / timeout |
| Whisper | Cold start tải model vào `/tmp` |
| CORS | `allow_origins=["*"]` |
