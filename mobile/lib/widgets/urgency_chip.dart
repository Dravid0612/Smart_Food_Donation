import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

class UrgencyChip extends StatelessWidget {
  final String urgency;

  const UrgencyChip({super.key, required this.urgency});

  Color _getUrgencyColor(String urgency) {
    switch (urgency.toLowerCase()) {
      case 'fresh':
        return AppTheme.urgencyFresh;
      case 'use soon':
        return AppTheme.urgencyUseSoon;
      case 'urgent':
        return AppTheme.urgencyUrgent;
      case 'expired':
        return AppTheme.urgencyExpired;
      default:
        return AppTheme.urgencyFresh;
    }
  }

  IconData _getUrgencyIcon(String urgency) {
    switch (urgency.toLowerCase()) {
      case 'fresh':
        return Icons.eco;
      case 'use soon':
        return Icons.access_time;
      case 'urgent':
        return Icons.warning_amber_rounded;
      case 'expired':
        return Icons.error_outline;
      default:
        return Icons.eco;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _getUrgencyColor(urgency);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_getUrgencyIcon(urgency), size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            urgency,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
