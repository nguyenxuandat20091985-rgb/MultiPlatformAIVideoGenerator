class JobStep {
  final String name;
  final String status;
  final String message;

  JobStep({
    required this.name,
    required this.status,
    this.message = '',
  });

  factory JobStep.fromJson(Map<String, dynamic> json) {
    return JobStep(
      name: json['name'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      message: json['message'] as String? ?? '',
    );
  }
}

class PublishResult {
  final String platform;
  final bool success;
  final String? postId;
  final String? url;
  final String message;

  PublishResult({
    required this.platform,
    required this.success,
    this.postId,
    this.url,
    this.message = '',
  });

  factory PublishResult.fromJson(Map<String, dynamic> json) {
    return PublishResult(
      platform: json['platform'] as String? ?? '',
      success: json['success'] as bool? ?? false,
      postId: json['post_id'] as String?,
      url: json['url'] as String?,
      message: json['message'] as String? ?? '',
    );
  }
}

class Job {
  final String jobId;
  final String status;
  final String createdAt;
  final String updatedAt;
  final Map<String, dynamic> request;
  final List<JobStep> steps;
  final int progressPercent;
  final String? videoUrl;
  final String? videoPath;
  final List<PublishResult>? publishResults;
  final String? error;

  Job({
    required this.jobId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.request,
    required this.steps,
    this.progressPercent = 0,
    this.videoUrl,
    this.videoPath,
    this.publishResults,
    this.error,
  });

  bool get isDone => status == 'completed' || status == 'failed';
  bool get isSuccess => status == 'completed';

  factory Job.fromJson(Map<String, dynamic> json) {
    final stepsJson = json['steps'] as List<dynamic>? ?? [];
    final publishJson = json['publish_results'] as List<dynamic>?;

    return Job(
      jobId: json['job_id'] as String? ?? '',
      status: json['status'] as String? ?? 'queued',
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      request: Map<String, dynamic>.from(json['request'] as Map? ?? {}),
      steps: stepsJson
          .map((e) => JobStep.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      progressPercent: json['progress_percent'] as int? ?? 0,
      videoUrl: json['video_url'] as String?,
      videoPath: json['video_path'] as String?,
      publishResults: publishJson
          ?.map((e) =>
              PublishResult.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      error: json['error'] as String?,
    );
  }
}
