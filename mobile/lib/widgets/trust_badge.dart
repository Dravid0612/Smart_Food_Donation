import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Compact trust badge conveying earned reliability without artificial giant scores
class TrustBadge extends StatelessWidget {
  final String label;
  final double? score;
  final bool isVerified;

  const TrustBadge({
    super.key,
    required this.label,
    this.score,
    this.isVerified = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space4),
      decoration: BoxDecoration(
        color: isVerified ? AppTheme.primaryGreen.withValues(alpha: 0.08) : AppTheme.background,
        borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
        border: Border.all(
          color: isVerified ? AppTheme.primaryGreen.withValues(alpha: 0.25) : AppTheme.border,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isVerified ? Icons.verified : Icons.shield_outlined,
            size: 14,
            color: isVerified ? AppTheme.primaryGreen : AppTheme.secondaryTerracotta,
          ),
          const SizedBox(width: AppTheme.space4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: isVerified ? AppTheme.primaryGreen : AppTheme.textPrimary,
            ),
          ),
          if (score != null) ...[
            const SizedBox(width: AppTheme.space4),
            Text(
              '${score!.toInt()}%',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
