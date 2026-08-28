import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../core/utils/food_rescue_status_helper.dart';

/// Semantic Rescue Urgency Badge:
/// Strictly displays RESCUE URGENCY (Fresh, Approaching, Urgent, Critical, Rescue window ended).
/// Never combines with contradictory text or ambiguous time fragments.
class UrgencyBadge extends StatelessWidget {
  final String level;
  final int? remainingMinutes;

  const UrgencyBadge({
    super.key,
    required this.level,
    this.remainingMinutes,
  });

  @override
  Widget build(BuildContext context) {
    final info = FoodRescueStatusHelper.getRescueUrgency(
      context,
      level,
      remainingMinutes: remainingMinutes,
    );

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space4),
      decoration: BoxDecoration(
        color: info.backgroundColor,
        borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
        border: Border.all(color: info.borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(info.icon, size: 14, color: info.color),
          const SizedBox(width: AppTheme.space4),
          Text(
            info.label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: info.color,
            ),
          ),
        ],
      ),
    );
  }
}
