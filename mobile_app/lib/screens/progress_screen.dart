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

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _poll());
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
        await Future.delayed(const Duration(milliseconds: 400));
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

  @override
  Widget build(BuildContext context) {
    final job = _job;
    final progress = (job?.progressPercent ?? 0).clamp(0, 100) / 100.0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Generating…'),
        automaticallyImplyLeading: job?.isDone != true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null)
                Card(
                  color: Colors.red.shade50,
                  child: ListTile(
                    leading: const Icon(Icons.error, color: Colors.red),
                    title: Text(_error!),
                  ),
                ),
              const SizedBox(height: 8),
              Text(
                job == null ? 'Connecting…' : 'Status: ${job.status}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: job == null ? null : progress,
                minHeight: 10,
                borderRadius: BorderRadius.circular(6),
              ),
              const SizedBox(height: 6),
              Text(
                '${job?.progressPercent ?? 0}%',
                textAlign: TextAlign.end,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              Expanded(
                child: job == null
                    ? const Center(child: CircularProgressIndicator())
                    : ListView.builder(
                        itemCount: job.steps.length,
                        itemBuilder: (_, i) => StepTile(step: job.steps[i]),
                      ),
              ),
              Text(
                'Job ID: ${widget.jobId}',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.grey),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
