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

## Tải APK qua GitHub Actions (không cần Flutter trên máy)

1. Mở repo trên GitHub → tab **Actions**
2. Chọn **Build Android APK** → **Run workflow**
3. (Tuỳ chọn) nhập `api_base_url` (URL FastAPI, ví dụ `http://192.168.1.10:8000`)
4. Khi job xong → phần **Artifacts** → tải **app-release-apk** → giải nén ra `app-release.apk`

Workflow file: `.github/workflows/build_apk.yml` (tự chạy khi sửa `mobile_app/`, hoặc chạy tay).

## Build APK (Android) trên máy

```bash
cd mobile_app
flutter pub get
flutter build apk --release \
  --dart-define=API_BASE_URL=http://YOUR_SERVER_IP:8000
```

File APK:

```
build/app/outputs/flutter-apk/app-release.apk
```

Split APK theo ABI (nhẹ hơn):

```bash
flutter build apk --split-per-abi --release \
  --dart-define=API_BASE_URL=http://YOUR_SERVER_IP:8000
```

## Build App Bundle (Play Store)

```bash
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://your-api.example.com
```

## Build iOS

```bash
flutter build ios --release \
  --dart-define=API_BASE_URL=https://your-api.example.com
open ios/Runner.xcworkspace
```
