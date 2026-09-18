import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/job.dart';

class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = baseUrl ??
            const String.fromEnvironment(
              'API_BASE_URL',
              defaultValue: 'http://10.0.2.2:8000',
            );

  final String baseUrl;

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> health() async {
    final res = await http.get(_u('/health')).timeout(const Duration(seconds: 8));
    if (res.statusCode != 200) {
      throw Exception('Backend unreachable (${res.statusCode})');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
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

    final res = await http
        .post(
          _u('/api/v1/generate'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 30));

    if (res.statusCode != 200) {
      throw Exception('Generate failed: ${res.statusCode} ${res.body}');
    }
    return Job.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<Job> getJob(String jobId) async {
    final res = await http
        .get(_u('/api/v1/jobs/$jobId'))
        .timeout(const Duration(seconds: 15));
    if (res.statusCode == 404) {
      throw Exception('Job not found');
    }
    if (res.statusCode != 200) {
      throw Exception('Status error: ${res.statusCode}');
    }
    return Job.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  String videoAbsoluteUrl(String? relativeOrAbsolute) {
    if (relativeOrAbsolute == null || relativeOrAbsolute.isEmpty) return '';
    if (relativeOrAbsolute.startsWith('http')) return relativeOrAbsolute;
    return '$baseUrl$relativeOrAbsolute';
  }
}
