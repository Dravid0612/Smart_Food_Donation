import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../core/utils/food_rescue_status_helper.dart';

/// Semantic Visual Condition Badge:
/// Strictly displays VISUAL CONDITION (Good / Fair / Concerning / Inspection Required)
/// Never combines with confidence percentage without explicit labeling or food safety claims.
class ConditionBadge extends StatelessWidget {
  final String condition;
  final double? confidence;
  final bool showConfidenceLabel;

  const ConditionBadge({
    super.key,
    required this.condition,
    this.confidence,
    this.showConfidenceLabel = false,
  });

  @override
  Widget build(BuildContext context) {
    final info = FoodRescueStatusHelper.getVisualCondition(
      context,
      condition,
      confidence: confidence,
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
          if (showConfidenceLabel && info.confidenceDescription != null) ...[
            const SizedBox(width: AppTheme.space4),
            Text(
              '• ${info.confidenceDescription}',
              style: TextStyle(
                fontSize: 11,
                color: info.color.withValues(alpha: 0.85),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
