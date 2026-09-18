import 'package:flutter/material.dart';
import '../models/job.dart';

class StepTile extends StatelessWidget {
  final JobStep step;

  const StepTile({super.key, required this.step});

  IconData get _icon {
    switch (step.status) {
      case 'done':
        return Icons.check_circle;
      case 'running':
        return Icons.autorenew;
      case 'error':
        return Icons.error;
      default:
        return Icons.radio_button_unchecked;
    }
  }

  Color get _color {
    switch (step.status) {
      case 'done':
        return Colors.green;
      case 'running':
        return Colors.blue;
      case 'error':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String get _label {
    const map = {
      'script': 'Generating script',
      'image_prompts': 'Image prompts',
      'images': 'Generating images',
      'audio': 'Voiceover (TTS)',
      'compose': 'Composing video',
      'captions': 'Captions',
      'publish': 'Publishing',
    };
    return map[step.name] ?? step.name;
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: step.status == 'running'
          ? SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: _color,
              ),
            )
          : Icon(_icon, color: _color, size: 28),
      title: Text(
        _label,
        style: TextStyle(
          fontWeight:
              step.status == 'running' ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      subtitle: step.message.isNotEmpty ? Text(step.message) : null,
    );
  }
}
