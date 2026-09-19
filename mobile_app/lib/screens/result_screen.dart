import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:chewie/chewie.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';

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
  bool _loadingPlayer = true;

  String get _videoUrl => widget.api.videoAbsoluteUrl(widget.job.videoUrl);

  @override
  void initState() {
    super.initState();
    if (widget.job.isSuccess) {
      _initPlayer();
    } else {
      _loadingPlayer = false;
    }
  }

  Future<void> _initPlayer() async {
    setState(() {
      _loadingPlayer = true;
      _playerError = null;
    });
    if (_videoUrl.isEmpty) {
      setState(() {
        _loadingPlayer = false;
        _playerError = 'Không có đường dẫn video từ server.';
      });
      return;
    }
    try {
      _chewie?.dispose();
      _chewie = null;
      final old = _videoCtrl;
      _videoCtrl = null;
      await old?.dispose();
      final ctrl = VideoPlayerController.networkUrl(Uri.parse(_videoUrl));
      await ctrl.initialize().timeout(const Duration(seconds: 90));
      final chewie = ChewieController(
        videoPlayerController: ctrl,
        autoPlay: true,
        looping: true,
        allowFullScreen: true,
        allowMuting: true,
        showControls: true,
        aspectRatio:
            ctrl.value.aspectRatio == 0 ? 9 / 16 : ctrl.value.aspectRatio,
        materialProgressColors: ChewieProgressColors(
          playedColor: const Color(0xFF5B2EFF),
          handleColor: const Color(0xFF5B2EFF),
          bufferedColor: Colors.white24,
          backgroundColor: Colors.white12,
        ),
        errorBuilder: (_, msg) => Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(msg,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white)),
          ),
        ),
      );
      if (!mounted) return;
      setState(() {
        _videoCtrl = ctrl;
        _chewie = chewie;
        _loadingPlayer = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadingPlayer = false;
          _playerError =
              'Không phát được video.\n$e\n\nThử Mở trên trình duyệt.';
        });
      }
    }
  }

  Future<void> _openExternal() async {
    if (_videoUrl.isEmpty) return;
    final uri = Uri.parse(_videoUrl);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _snack('Không mở được trình duyệt');
    }
  }

  Future<void> _copyLink() async {
    if (_videoUrl.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: _videoUrl));
    _snack('Đã copy link video');
  }

  Future<void> _share() async {
    if (_videoUrl.isEmpty) return;
    await Share.share(
      'Video AI: $_videoUrl',
      subject: widget.job.request['title']?.toString() ?? 'AI Video',
    );
  }

  void _snack(String m) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
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
    final theme = Theme.of(context);
    final title = job.request['title']?.toString() ??
        job.request['topic']?.toString() ??
        'Video';

    return Scaffold(
      backgroundColor: ok ? Colors.black : null,
      appBar: AppBar(
        backgroundColor: ok ? Colors.black : null,
        foregroundColor: ok ? Colors.white : null,
        title: Text(ok ? 'Xem video' : 'Tạo video thất bại'),
        leading: IconButton(
          icon: const Icon(Icons.home),
          tooltip: 'Về trang chủ',
          onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
        ),
        actions: [
          if (ok && _videoUrl.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Tải lại player',
              onPressed: _initPlayer,
            ),
        ],
      ),
      body: ok ? _buildSuccess(theme, title) : _buildFailed(theme, job),
    );
  }

  Widget _buildFailed(ThemeData theme, Job job) {
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: Colors.red.shade50,
            child: ListTile(
              leading: const Icon(Icons.error, color: Colors.red, size: 36),
              title: const Text('Không tạo được video'),
              subtitle: Text(job.error ?? 'Lỗi không xác định'),
            ),
          ),
          const SizedBox(height: 12),
          Text('Các bước', style: theme.textTheme.titleMedium),
          ...job.steps.map(
            (s) => ListTile(
              dense: true,
              leading: Icon(
                s.status == 'done'
                    ? Icons.check_circle
                    : s.status == 'error'
                        ? Icons.cancel
                        : Icons.circle_outlined,
                color: s.status == 'done'
                    ? Colors.green
                    : s.status == 'error'
                        ? Colors.red
                        : Colors.grey,
              ),
              title: Text(s.name),
              subtitle: s.message.isEmpty ? null : Text(s.message),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () =>
                Navigator.of(context).popUntil((r) => r.isFirst),
            icon: const Icon(Icons.home),
            label: const Text('Về trang chủ'),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccess(ThemeData theme, String title) {
    return Column(
      children: [
        Expanded(
          child: Center(
            child: AspectRatio(
              aspectRatio: 9 / 16,
              child: Container(
                color: Colors.black,
                child: _loadingPlayer
                    ? const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(color: Colors.white),
                          SizedBox(height: 12),
                          Text('Đang tải video…',
                              style: TextStyle(color: Colors.white70)),
                        ],
                      )
                    : _chewie != null
                        ? Chewie(controller: _chewie!)
                        : Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.videocam_off,
                                    color: Colors.white54, size: 48),
                                const SizedBox(height: 12),
                                Text(
                                  _playerError ?? 'Không phát được',
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                      color: Colors.white70, height: 1.4),
                                ),
                                const SizedBox(height: 16),
                                FilledButton.tonal(
                                  onPressed: _initPlayer,
                                  child: const Text('Thử lại'),
                                ),
                              ],
                            ),
                          ),
              ),
            ),
          ),
        ),
        Container(
          width: double.infinity,
          color: Theme.of(context).scaffoldBackgroundColor,
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.w600),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.check_circle,
                          size: 16, color: Colors.green.shade600),
                      const SizedBox(width: 6),
                      Text('Video đã sẵn sàng',
                          style: TextStyle(
                              color: Colors.green.shade700, fontSize: 13)),
                    ],
                  ),
                  if (_videoUrl.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    SelectableText(
                      _videoUrl,
                      style: theme.textTheme.bodySmall?.copyWith(
                          color: Colors.grey.shade600, fontSize: 11),
                    ),
                  ],
                  if (jobHasPublish) ...[
                    const SizedBox(height: 12),
                    Text('Đăng bài', style: theme.textTheme.titleSmall),
                    const SizedBox(height: 6),
                    ...widget.job.publishResults!.map(
                      (r) => Card(
                        margin: const EdgeInsets.only(bottom: 6),
                        child: ListTile(
                          dense: true,
                          leading: Icon(
                            r.success ? Icons.check_circle : Icons.cancel,
                            color: r.success ? Colors.green : Colors.red,
                          ),
                          title: Text(r.platform.toUpperCase()),
                          subtitle: Text(
                            r.message.isNotEmpty
                                ? r.message
                                : (r.url ?? r.postId ?? ''),
                            maxLines: 2,
                          ),
                          onTap: r.url != null && r.url!.isNotEmpty
                              ? () => launchUrl(Uri.parse(r.url!),
                                  mode: LaunchMode.externalApplication)
                              : null,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _videoUrl.isEmpty ? null : _copyLink,
                          icon: const Icon(Icons.link, size: 18),
                          label: const Text('Copy link'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _videoUrl.isEmpty ? null : _openExternal,
                          icon: const Icon(Icons.open_in_browser, size: 18),
                          label: const Text('Trình duyệt'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _videoUrl.isEmpty ? null : _share,
                          icon: const Icon(Icons.share, size: 18),
                          label: const Text('Chia sẻ'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: () => Navigator.of(context)
                              .popUntil((r) => r.isFirst),
                          icon: const Icon(Icons.add, size: 18),
                          label: const Text('Tạo video mới'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  bool get jobHasPublish =>
      widget.job.publishResults != null &&
      widget.job.publishResults!.isNotEmpty;
}
