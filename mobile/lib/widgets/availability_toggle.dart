import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../providers/volunteer_task_provider.dart';

/// Persistent availability toggle for Volunteer AppBar: 🟢 Available, 🟡 Busy, ⚫ Offline
class AvailabilityToggle extends StatelessWidget {
  final String? currentStatus; // 'available', 'busy', 'offline'
  final ValueChanged<String>? onStatusChanged;
  final bool isLoading;

  const AvailabilityToggle({
    super.key,
    this.currentStatus,
    this.onStatusChanged,
    this.isLoading = false,
  });

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'available':
        return AppTheme.success;
      case 'busy':
        return AppTheme.warning;
      case 'offline':
      default:
        return AppTheme.disabled;
    }
  }

  String _getLabel(BuildContext context, String status) {
    switch (status.toLowerCase()) {
      case 'available':
        return context.tr('available');
      case 'busy':
        return context.tr('busy');
      case 'offline':
      default:
        return context.tr('offline');
    }
  }

  @override
  Widget build(BuildContext context) {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final effectiveStatus = currentStatus ?? (taskProv.isAvailable ? 'available' : 'offline');
    final norm = effectiveStatus.toLowerCase();
    final color = _getStatusColor(norm);

    return PopupMenuButton<String>(
      onSelected: (val) {
        if (onStatusChanged != null) {
          onStatusChanged!(val);
        } else {
          taskProv.setAvailability(val == 'available');
        }
      },
      enabled: !isLoading,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        side: const BorderSide(color: AppTheme.border),
      ),
      color: AppTheme.card,
      itemBuilder: (ctx) => [
        _buildMenuItem('available', '🟢 ${ctx.tr('available')}', AppTheme.success),
        _buildMenuItem('busy', '🟡 ${ctx.tr('busy')}', AppTheme.warning),
        _buildMenuItem('offline', '⚫ ${ctx.tr('offline')}', AppTheme.disabled),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space12, vertical: AppTheme.space8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
          border: Border.all(color: color.withValues(alpha: 0.35)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isLoading)
              const SizedBox(
                width: 10,
                height: 10,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
            const SizedBox(width: AppTheme.space8),
            Text(
              _getLabel(context, norm),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(width: AppTheme.space4),
            Icon(Icons.arrow_drop_down, size: 16, color: color),
          ],
        ),
      ),
    );
  }

  PopupMenuItem<String> _buildMenuItem(String val, String text, Color color) {
    return PopupMenuItem<String>(
      value: val,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: AppTheme.space8),
          Flexible(
            child: Text(
              text,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
