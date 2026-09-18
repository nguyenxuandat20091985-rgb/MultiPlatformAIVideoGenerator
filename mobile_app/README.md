# Flutter Mobile App — MultiPlatform AI Video Generator

Client di động (Android / iOS) kết nối tới FastAPI backend (`api.py`).

## Tính năng

- Nhập Topic, Title, Tags, Style
- Bật/tắt đăng YouTube · TikTok · Facebook
- Gửi job tới API → theo dõi tiến trình từng bước
- Xem trước video khi hoàn tất + kết quả publish

## Yêu cầu

- Flutter SDK **3.16+** ([flutter.dev](https://flutter.dev))
- Backend đang chạy: `python api.py` (port **8000**)

## Cấu hình API URL

| Môi trường | Base URL |
|------------|----------|
| Android emulator | `http://10.0.2.2:8000` (mặc định) |
| iOS simulator | `http://127.0.0.1:8000` |
| Máy thật (cùng Wi‑Fi) | `http://IP_MÁY_TÍNH:8000` |

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

## Lần đầu setup

```bash
cd mobile_app
flutter create . --project-name multiplatform_ai_video
flutter pub get
flutter run
```

## Build APK

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=http://YOUR_SERVER_IP:8000
# → build/app/outputs/flutter-apk/app-release.apk
```
