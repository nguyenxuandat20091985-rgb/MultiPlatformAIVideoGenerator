import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/job.dart';
import 'settings_service.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.cause});
  final String message;
  final Object? cause;

  @override
  String toString() => message;
}

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

  static String _normalize(String url) {
    var u = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (!u.startsWith('http://') && !u.startsWith('https://')) {
      final host = u.toLowerCase();
      if (host.contains('onrender.com') ||
          host.contains('hf.space') ||
          host.contains('railway.app') ||
          host.contains('fly.dev')) {
        u = 'https://$u';
      } else {
        u = 'http://$u';
      }
    }
    if (u.startsWith('http://') &&
        (u.contains('onrender.com') || u.contains('hf.space'))) {
      u = 'https://${u.substring('http://'.length)}';
    }
    return u;
  }

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
      final isCloud = baseUrl.contains('onrender.com') ||
          baseUrl.contains('hf.space') ||
          baseUrl.contains('railway');
      throw ApiException(
        isCloud
            ? 'Hết thời gian chờ ${timeout.inSeconds}s tới $baseUrl\n'
                'Render Free có thể đang ngủ — mở link /health trên Chrome '
                'đợi 1 phút rồi bấm Kiểm tra lại.'
            : 'Không kết nối được server trong ${timeout.inSeconds}s.\n'
                'URL hiện tại: $baseUrl',
      );
    } on SocketException catch (e) {
      throw ApiException(
        'Không kết nối được tới $baseUrl\nChi tiết: ${e.message}',
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
      timeout: const Duration(seconds: 60),
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
      timeout: const Duration(seconds: 90),
    );
  }

  Future<Job> getJob(String jobId) async {
    return _withFriendlyErrors(
      () async {
        // Render can briefly return 502/503/504 while a worker is waking or
        // restarting. Do not turn a transient gateway error into a dead job.
        const retryable = {502, 503, 504};
        const delays = [
          Duration(seconds: 2),
          Duration(seconds: 5),
          Duration(seconds: 10),
        ];
        http.Response? last;
        for (var attempt = 0; attempt < 4; attempt++) {
          final res = await http.get(_u('/api/v1/jobs/$jobId'));
          if (res.statusCode == 200) {
            return Job.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
          }
          if (res.statusCode == 404) {
            throw ApiException('Không tìm thấy job $jobId');
          }
          last = res;
          if (!retryable.contains(res.statusCode) || attempt == 3) break;
          await Future<void>.delayed(delays[attempt]);
        }
        final status = last?.statusCode ?? 0;
        if (retryable.contains(status)) {
          throw ApiException(
            'Server đang khởi động lại (HTTP $status). '
            'Job $jobId vẫn được giữ trên màn hình; hãy kiểm tra lại sau vài giây.',
          );
        }
        throw ApiException('Lỗi trạng thái job ($status)');
      },
      timeout: const Duration(seconds: 75),
    );
  }

  String videoAbsoluteUrl(String? relativeOrAbsolute) {
    if (relativeOrAbsolute == null || relativeOrAbsolute.isEmpty) return '';
    if (relativeOrAbsolute.startsWith('http')) return relativeOrAbsolute;
    return '$baseUrl$relativeOrAbsolute';
  }
}
