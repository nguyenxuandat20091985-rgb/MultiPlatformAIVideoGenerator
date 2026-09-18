import 'package:flutter/material.dart';

class PlatformSwitch extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final bool value;
  final ValueChanged<bool> onChanged;

  const PlatformSwitch({
    super.key,
    required this.label,
    required this.icon,
    required this.color,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: value ? 2 : 0,
      color: value ? color.withOpacity(0.12) : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: value ? color : Colors.grey.shade300,
          width: value ? 1.5 : 1,
        ),
      ),
      child: SwitchListTile(
        secondary: Icon(icon, color: value ? color : Colors.grey),
        title: Text(
          label,
          style: TextStyle(
            fontWeight: value ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
        value: value,
        activeColor: color,
        onChanged: onChanged,
      ),
    );
  }
}
