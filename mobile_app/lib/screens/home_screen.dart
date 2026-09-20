import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_service.dart';
import '../services/settings_service.dart';
import '../widgets/platform_switch.dart';
import 'progress_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;
  final ValueChanged<String>? onApiUrlChanged;

  const HomeScreen({
    super.key,
    required this.api,
    this.onApiUrlChanged,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _topicCtrl = TextEditingController();
  final _titleCtrl = TextEditingController();
  final _tagsCtrl = TextEditingController();
  final _ctaCtrl = TextEditingController(text: 'Follow for more!');
  final _apiUrlCtrl = TextEditingController();

  String _style = 'educational';
  bool _youtube = true;
  bool _tiktok = false;
  bool _facebook = false;
  bool _skipCaptions = true;
  bool _busy = false;
  bool _pinging = false;
  String? _backendError;
  bool _backendOk = false;

  static const _styles = [
    'educational',
    'funny',
    'inspirational',
    'storytelling',
    'news',
    'product',
  ];

  @override
  void initState() {
    super.initState();
    _apiUrlCtrl.text = widget.api.baseUrl;
    _pingBackend();
  }

  Future<void> _pingBackend() async {
    setState(() {
      _pinging = true;
      _backendError = null;
    });
    try {
      await widget.api.health();
      if (mounted) {
        setState(() {
          _backendOk = true;
          _backendError = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _backendOk = false;
          _backendError = e.toString();
        });
      }
    } finally {
      if (mounted) setState(() => _pinging = false);
    }
  }

  Future<void> _saveApiUrl() async {
    var url = _apiUrlCtrl.text.trim();
    if (url.isEmpty) {
      _showSnack('Nhập API Base URL', error: true);
      return;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
      _apiUrlCtrl.text = url;
    }
    final uri = Uri.tryParse(url);
    if (uri == null || uri.host.isEmpty) {
      _showSnack('URL không hợp lệ', error: true);
      return;
    }

    await SettingsService.instance.setApiBaseUrl(url);
    widget.api.setBaseUrl(url);
    widget.onApiUrlChanged?.call(url);
    if (mounted) {
      setState(() {});
      _showSnack('Đã lưu API URL');
      await _pingBackend();
    }
  }

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: error ? Colors.red.shade700 : null,
        duration: Duration(seconds: error ? 5 : 2),
      ),
    );
  }

  Future<void> _submit() async {
    final topic = _topicCtrl.text.trim();
    if (topic.length < 3) {
      _showSnack('Nhập topic (ít nhất 3 ký tự)', error: true);
      return;
    }

    final platforms = <String>[];
    if (_youtube) platforms.add('youtube');
    if (_tiktok) platforms.add('tiktok');
    if (_facebook) platforms.add('facebook');

    final tags = _tagsCtrl.text
        .split(',')
        .map((t) => t.trim())
        .where((t) => t.isNotEmpty)
        .toList();

    setState(() => _busy = true);
    try {
      final job = await widget.api.startGenerate(
        topic: topic,
        title: _titleCtrl.text.trim().isEmpty ? topic : _titleCtrl.text.trim(),
        style: _style,
        cta: _ctaCtrl.text.trim().isEmpty ? 'Follow for more!' : _ctaCtrl.text.trim(),
        tags: tags,
        platforms: platforms,
        skipCaptions: _skipCaptions,
      );

      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ProgressScreen(api: widget.api, jobId: job.jobId),
        ),
      );
    } catch (e) {
      if (mounted) {
        _showSnack(e.toString(), error: true);
        setState(() {
          _backendOk = false;
          _backendError = e.toString();
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _topicCtrl.dispose();
    _titleCtrl.dispose();
    _tagsCtrl.dispose();
    _ctaCtrl.dispose();
    _apiUrlCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Video Generator'),
        actions: [
          IconButton(
            icon: _pinging
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    _backendOk ? Icons.cloud_done : Icons.cloud_off,
                    color: _backendOk ? Colors.green : Colors.orange,
                  ),
            tooltip: 'Kiểm tra kết nối API',
            onPressed: _pinging ? null : _pingBackend,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.settings_ethernet,
                            color: theme.colorScheme.primary),
                        const SizedBox(width: 8),
                        Text('API Base URL',
                            style: theme.textTheme.titleMedium),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Nhà máy (server): URL Render hoặc Cloudflare Tunnel.\n'
                      'Ví dụ: https://xxx.onrender.com hoặc https://xxx.trycloudflare.com',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _apiUrlCtrl,
                      decoration: InputDecoration(
                        labelText: 'https://…',
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.link),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.content_paste),
                          tooltip: 'Dán từ clipboard',
                          onPressed: () async {
                            final data =
                                await Clipboard.getData(Clipboard.kTextPlain);
                            final t = data?.text?.trim();
                            if (t != null && t.isNotEmpty) {
                              setState(() => _apiUrlCtrl.text = t);
                            }
                          },
                        ),
                      ),
                      keyboardType: TextInputType.url,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _saveApiUrl(),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _pinging ? null : _pingBackend,
                            icon: const Icon(Icons.network_check, size: 18),
                            label: const Text('Kiểm tra'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton.tonalIcon(
                            onPressed: _saveApiUrl,
                            icon: const Icon(Icons.save, size: 18),
                            label: const Text('Lưu URL'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            if (_backendError != null) ...[
              const SizedBox(height: 10),
              Card(
                color: Colors.orange.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.warning_amber, color: Colors.orange),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _backendError!,
                          style: const TextStyle(height: 1.35),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (_backendOk) ...[
              const SizedBox(height: 8),
              Card(
                color: Colors.green.shade50,
                child: const ListTile(
                  dense: true,
                  leading: Icon(Icons.check_circle, color: Colors.green),
                  title: Text('Đã kết nối nhà máy (API) thành công'),
                ),
              ),
            ],
            const SizedBox(height: 16),
            Text('Tạo video ngắn', style: theme.textTheme.titleLarge),
            const SizedBox(height: 12),
            TextField(
              controller: _topicCtrl,
              decoration: const InputDecoration(
                labelText: 'Topic *',
                hintText: 'e.g. 5 tips to stay productive',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lightbulb_outline),
              ),
              textInputAction: TextInputAction.next,
              maxLines: 2,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _titleCtrl,
              decoration: const InputDecoration(
                labelText: 'Title (optional)',
                hintText: 'Defaults to topic',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.title),
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _style,
              decoration: const InputDecoration(
                labelText: 'Style',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.style),
              ),
              items: _styles
                  .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                  .toList(),
              onChanged: (v) => setState(() => _style = v ?? 'educational'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _tagsCtrl,
              decoration: const InputDecoration(
                labelText: 'Tags (comma-separated)',
                hintText: 'productivity, tips, ai',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.tag),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _ctaCtrl,
              decoration: const InputDecoration(
                labelText: 'Call to action',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.campaign),
              ),
            ),
            const SizedBox(height: 20),
            Text('Đăng lên', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            PlatformSwitch(
              label: 'YouTube Shorts',
              icon: Icons.play_circle_filled,
              color: Colors.red,
              value: _youtube,
              onChanged: (v) => setState(() => _youtube = v),
            ),
            PlatformSwitch(
              label: 'TikTok',
              icon: Icons.music_note,
              color: Colors.black87,
              value: _tiktok,
              onChanged: (v) => setState(() => _tiktok = v),
            ),
            PlatformSwitch(
              label: 'Facebook Reels',
              icon: Icons.facebook,
              color: const Color(0xFF1877F2),
              value: _facebook,
              onChanged: (v) => setState(() => _facebook = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Bỏ phụ đề (nhẹ hơn, ít lỗi RAM)'),
              subtitle: const Text('Nên bật trên Render Free / máy yếu'),
              value: _skipCaptions,
              onChanged: (v) => setState(() => _skipCaptions = v),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                onPressed: _busy ? null : _submit,
                icon: _busy
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.rocket_launch),
                label: Text(
                  _busy ? 'Đang gửi…' : 'Tạo & Đăng',
                  style: const TextStyle(fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Nhà máy (server) làm video; app chỉ ra lệnh và xem kết quả.',
              style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
