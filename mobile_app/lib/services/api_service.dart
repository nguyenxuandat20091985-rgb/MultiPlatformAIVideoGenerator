import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/job.dart';
import 'settings_service.dart';

/// Friendly network / API errors for UI.
class ApiException implements Exception {
  ApiException(this.message, {this.cause});
  final String message;
  final Object? cause;

  @override
  String toString() => message;
}

/// Backend client. Base URL can be changed at runtime (device settings).
class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = _normalize(
          baseUrl ??
              const String.fromEnvironment(
                'API_BASE_URL',
                defaultValue: SettingsService.defaultApiBaseUrl,
              ),
        );

  String baseUrl;

  static String _normalize(String url) =>
      url.trim().replaceAll(RegExp(r'/+$'), '');

  void setBaseUrl(String url) {
    baseUrl = _normalize(url);
  }

  Uri _u(String path) {
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$p');
  }

  Future<T> _withFriendlyErrors<T>(
    Future<T> Function() action, {
    required Duration timeout,
  }) async {
    try {
      return await action().timeout(timeout);
    } on TimeoutException {
      throw ApiException(
        'Không kết nối được server trong ${timeout.inSeconds}s.\n'
        'Kiểm tra API Base URL ($baseUrl) và máy chạy python api.py '
        'cùng Wi‑Fi với điện thoại.',
      );
    } on SocketException catch (e) {
      throw ApiException(
        'Không kết nối được tới $baseUrl\n'
        '• Điện thoại thật: dùng IP LAN của máy tính (vd http://192.168.1.10:8000)\n'
        '• Emulator Android: http://10.0.2.2:8000\n'
        '• Đảm bảo firewall cho phép cổng 8000\n'
        'Chi tiết: ${e.message}',
        cause: e,
      );
    } on http.ClientException catch (e) {
      throw ApiException(
        'Lỗi mạng tới $baseUrl\n${e.message}',
        cause: e,
      );
    } on FormatException catch (e) {
      throw ApiException('Phản hồi API không hợp lệ: $e', cause: e);
    }
  }

  Future<Map<String, dynamic>> health() async {
    return _withFriendlyErrors(
      () async {
        final res = await http.get(_u('/health'));
        if (res.statusCode != 200) {
          throw ApiException(
            'Backend trả về ${res.statusCode}. URL: $baseUrl',
          );
        }
        return jsonDecode(res.body) as Map<String, dynamic>;
      },
      timeout: const Duration(seconds: 5),
    );
  }

  Future<Job> startGenerate({
    required String topic,
    String? title,
    String style = 'educational',
    String targetAudience = 'general',
    String cta = 'Follow for more!',
    List<String> tags = const [],
    List<String> platforms = const [],
    bool skipCaptions = false,
  }) async {
    final body = {
      'topic': topic,
      'title': title ?? topic,
      'style': style,
      'target_audience': targetAudience,
      'cta': cta,
      'tags': tags,
      'platforms': platforms,
      'skip_captions': skipCaptions,
    };

    return _withFriendlyErrors(
      () async {
        final res = await http.post(
          _u('/api/v1/generate'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        );
        if (res.statusCode != 200) {
          throw ApiException(
            'Tạo job thất bại (${res.statusCode}): ${res.body}',
          );
        }
        return Job.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
      },
      timeout: const Duration(seconds: 12),
    );
  }

  Future<Job> getJob(String jobId) async {
    return _withFriendlyErrors(
      () async {
        final res = await http.get(_u('/api/v1/jobs/$jobId'));
        if (res.statusCode == 404) {
          throw ApiException('Không tìm thấy job $jobId');
        }
        if (res.statusCode != 200) {
          throw ApiException('Lỗi trạng thái job (${res.statusCode})');
        }
        return Job.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
      },
      timeout: const Duration(seconds: 8),
    );
  }

  String videoAbsoluteUrl(String? relativeOrAbsolute) {
    if (relativeOrAbsolute == null || relativeOrAbsolute.isEmpty) return '';
    if (relativeOrAbsolute.startsWith('http')) return relativeOrAbsolute;
    return '$baseUrl$relativeOrAbsolute';
  }
}
