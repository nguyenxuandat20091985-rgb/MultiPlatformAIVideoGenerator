import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/platform_switch.dart';
import 'progress_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;

  const HomeScreen({super.key, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _topicCtrl = TextEditingController();
  final _titleCtrl = TextEditingController();
  final _tagsCtrl = TextEditingController();
  final _ctaCtrl = TextEditingController(text: 'Follow for more!');

  String _style = 'educational';
  bool _youtube = true;
  bool _tiktok = false;
  bool _facebook = false;
  bool _busy = false;
  String? _backendError;

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
    _pingBackend();
  }

  Future<void> _pingBackend() async {
    try {
      await widget.api.health();
      if (mounted) setState(() => _backendError = null);
    } catch (e) {
      if (mounted) {
        setState(() => _backendError =
            'Cannot reach API at ${widget.api.baseUrl}');
      }
    }
  }

  Future<void> _submit() async {
    final topic = _topicCtrl.text.trim();
    if (topic.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Please enter a topic (min 3 characters)')),
      );
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
        title: _titleCtrl.text.trim().isEmpty
            ? topic
            : _titleCtrl.text.trim(),
        style: _style,
        cta: _ctaCtrl.text.trim().isEmpty
            ? 'Follow for more!'
            : _ctaCtrl.text.trim(),
        tags: tags,
        platforms: platforms,
      );

      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) =>
              ProgressScreen(api: widget.api, jobId: job.jobId),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Error: $e'), backgroundColor: Colors.red),
        );
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
            icon: const Icon(Icons.refresh),
            tooltip: 'Check backend',
            onPressed: _pingBackend,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_backendError != null)
              Card(
                color: Colors.orange.shade50,
                child: ListTile(
                  leading: const Icon(Icons.warning_amber,
                      color: Colors.orange),
                  title: Text(_backendError!),
                  subtitle: const Text(
                    'Start the API: python api.py\n'
                    'Emulator uses 10.0.2.2 — real device needs your PC LAN IP.',
                  ),
                ),
              ),
            const SizedBox(height: 8),
            Text('Create short-form video',
                style: theme.textTheme.titleLarge),
            const SizedBox(height: 16),
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
                  .map((s) =>
                      DropdownMenuItem(value: s, child: Text(s)))
                  .toList(),
              onChanged: (v) =>
                  setState(() => _style = v ?? 'educational'),
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
            Text('Publish to', style: theme.textTheme.titleMedium),
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
            const SizedBox(height: 24),
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
                  _busy ? 'Starting…' : 'Create & Publish',
                  style: const TextStyle(fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Generation may take several minutes (AI images + TTS + encode).',
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
