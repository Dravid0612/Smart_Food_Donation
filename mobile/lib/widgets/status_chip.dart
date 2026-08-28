import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  final String status;

  const StatusChip({super.key, required this.status});

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return AppTheme.statusPending;
      case 'accepted':
        return AppTheme.statusAccepted;
      case 'volunteer_assigned':
      case 'assigned':
        return AppTheme.statusAssigned;
      case 'collected':
      case 'in_transit':
        return AppTheme.statusCollected;
      case 'delivered':
      case 'completed':
        return AppTheme.statusDelivered;
      case 'rejected':
      case 'expired':
      case 'cancelled':
        return AppTheme.statusExpired;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _getStatusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3), width: 1),
      ),
      child: Text(
        context.trStatus(status),
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
