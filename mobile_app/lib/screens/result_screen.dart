import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import 'package:chewie/chewie.dart';
import '../models/job.dart';
import '../services/api_service.dart';

class ResultScreen extends StatefulWidget {
  final ApiService api;
  final Job job;

  const ResultScreen({super.key, required this.api, required this.job});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  VideoPlayerController? _videoCtrl;
  ChewieController? _chewie;
  String? _playerError;

  @override
  void initState() {
    super.initState();
    _initPlayer();
  }

  Future<void> _initPlayer() async {
    final url = widget.api.videoAbsoluteUrl(widget.job.videoUrl);
    if (url.isEmpty) {
      setState(() => _playerError = 'No video URL');
      return;
    }
    try {
      final ctrl = VideoPlayerController.networkUrl(Uri.parse(url));
      await ctrl.initialize();
      final chewie = ChewieController(
        videoPlayerController: ctrl,
        autoPlay: true,
        looping: false,
        aspectRatio: ctrl.value.aspectRatio == 0
            ? 9 / 16
            : ctrl.value.aspectRatio,
        errorBuilder: (_, msg) => Center(child: Text(msg)),
      );
      if (!mounted) return;
      setState(() {
        _videoCtrl = ctrl;
        _chewie = chewie;
      });
    } catch (e) {
      if (mounted) setState(() => _playerError = e.toString());
    }
  }

  @override
  void dispose() {
    _chewie?.dispose();
    _videoCtrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final job = widget.job;
    final ok = job.isSuccess;

    return Scaffold(
      appBar: AppBar(
        title: Text(ok ? 'Video ready' : 'Failed'),
        leading: IconButton(
          icon: const Icon(Icons.home),
          onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (!ok) ...[
              Card(
                color: Colors.red.shade50,
                child: ListTile(
                  leading: const Icon(Icons.error, color: Colors.red),
                  title: const Text('Generation failed'),
                  subtitle: Text(job.error ?? 'Unknown error'),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (ok) ...[
              AspectRatio(
                aspectRatio: 9 / 16,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: _chewie != null
                      ? Chewie(controller: _chewie!)
                      : Container(
                          color: Colors.black12,
                          child: Center(
                            child: _playerError != null
                                ? Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Text(
                                      _playerError!,
                                      textAlign: TextAlign.center,
                                    ),
                                  )
                                : const CircularProgressIndicator(),
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 12),
              if (job.videoUrl != null)
                SelectableText(
                  widget.api.videoAbsoluteUrl(job.videoUrl),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
            if (job.publishResults != null &&
                job.publishResults!.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text('Publish results',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...job.publishResults!.map(
                (r) => Card(
                  child: ListTile(
                    leading: Icon(
                      r.success ? Icons.check_circle : Icons.cancel,
                      color: r.success ? Colors.green : Colors.red,
                    ),
                    title: Text(r.platform.toUpperCase()),
                    subtitle: Text(
                      r.message.isNotEmpty
                          ? r.message
                          : (r.url ?? r.postId ?? ''),
                    ),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () =>
                  Navigator.of(context).popUntil((r) => r.isFirst),
              icon: const Icon(Icons.add),
              label: const Text('Create another'),
            ),
          ],
        ),
      ),
    );
  }
}
