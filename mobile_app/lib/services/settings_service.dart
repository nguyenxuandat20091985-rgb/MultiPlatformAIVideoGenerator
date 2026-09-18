import 'package:shared_preferences/shared_preferences.dart';

/// Persists user preferences (API base URL, etc.) on device.
class SettingsService {
  SettingsService._();
  static final SettingsService instance = SettingsService._();

  static const _keyApiBaseUrl = 'api_base_url';

  /// Default for Android emulator (maps to host localhost).
  static const defaultApiBaseUrl = 'http://10.0.2.2:8000';

  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  Future<String> getApiBaseUrl() async {
    await init();
    final v = _prefs!.getString(_keyApiBaseUrl);
    if (v == null || v.trim().isEmpty) return defaultApiBaseUrl;
    return v.trim().replaceAll(RegExp(r'/+$'), '');
  }

  Future<void> setApiBaseUrl(String url) async {
    await init();
    final cleaned = url.trim().replaceAll(RegExp(r'/+$'), '');
    await _prefs!.setString(_keyApiBaseUrl, cleaned);
  }
}
