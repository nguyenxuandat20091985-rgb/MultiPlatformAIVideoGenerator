import 'dart:async';
import 'package:flutter/material.dart';
import '../models/job.dart';
import '../services/api_service.dart';
import '../widgets/step_tile.dart';
import 'result_screen.dart';

class ProgressScreen extends StatefulWidget {
  final ApiService api;
  final String jobId;

  const ProgressScreen({
    super.key,
    required this.api,
    required this.jobId,
  });

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  Job? _job;
  String? _error;
  Timer? _timer;
  bool _navigated = false;

  static const _labels = {
    'script': 'Viết kịch bản',
    'image_prompts': 'Tạo mô tả ảnh',
    'images': 'Sinh ảnh AI',
    'audio': 'Giọng nói (TTS)',
    'compose': 'Ghép video',
    'captions': 'Phụ đề',
    'publish': 'Đăng nền tảng',
  };

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _poll());
  }

  Future<void> _poll() async {
    try {
      final job = await widget.api.getJob(widget.jobId);
      if (!mounted) return;
      setState(() {
        _job = job;
        _error = null;
      });

      if (job.isDone && !_navigated) {
        _navigated = true;
        _timer?.cancel();
        await Future.delayed(const Duration(milliseconds: 500));
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ResultScreen(api: widget.api, job: job),
          ),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String _statusLabel(String s) {
    switch (s) {
      case 'queued':
        return 'Đang xếp hàng…';
      case 'running':
        return 'Đang tạo video…';
      case 'completed':
        return 'Hoàn tất';
      case 'failed':
        return 'Thất bại';
      default:
        return s;
    }
  }

  @override
  Widget build(BuildContext context) {
    final job = _job;
    final progress = (job?.progressPercent ?? 0).clamp(0, 100) / 100.0;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Đang tạo video'),
        automaticallyImplyLeading: job?.isDone != true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                elevation: 0,
                color: theme.colorScheme.primaryContainer.withOpacity(0.35),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Icon(
                        job?.status == 'failed'
                            ? Icons.error_outline
                            : Icons.movie_creation_outlined,
                        size: 40,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        job == null
                            ? 'Đang kết nối server…'
                            : _statusLabel(job.status),
                        style: theme.textTheme.titleLarge,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Có thể mất vài phút (AI + TTS + encode).\n'
                        'Giữ màn hình này để theo dõi.',
                        style: theme.textTheme.bodySmall
                            ?.copyWith(color: Colors.grey.shade700),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Card(
                  color: Colors.red.shade50,
                  child: ListTile(
                    leading: const Icon(Icons.warning, color: Colors.red),
                    title: Text(_error!, style: const TextStyle(fontSize: 13)),
                    trailing: IconButton(
                      icon: const Icon(Icons.refresh),
                      onPressed: _poll,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: LinearProgressIndicator(
                      value: job == null ? null : progress,
                      minHeight: 12,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${job?.progressPercent ?? 0}%',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text('Các bước', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Expanded(
                child: job == null
                    ? const Center(child: CircularProgressIndicator())
                    : ListView.builder(
                        itemCount: job.steps.length,
                        itemBuilder: (_, i) {
                          final s = job.steps[i];
                          final label = _labels[s.name] ?? s.name;
                          return StepTile(
                            step: JobStep(
                              name: label,
                              status: s.status,
                              message: s.message,
                            ),
                          );
                        },
                      ),
              ),
              Text(
                'Job: ${widget.jobId}',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: Colors.grey, fontSize: 11),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
