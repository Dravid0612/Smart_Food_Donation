import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../models/feedback_model.dart';

/// Renders explainable reliability badges and indicators.
/// Enforces sample-size protection with neutral status labels.
class TrustIndicatorWidget extends StatelessWidget {
  final ReliabilityProfileModel? profile;
  final double? score;
  final String? trustTier;
  final List<String>? badges;
  final bool compact;

  const TrustIndicatorWidget({
    super.key,
    this.profile,
    this.score,
    this.trustTier,
    this.badges,
    this.compact = false,
  });

  Color _getTierColor(double sc) {
    if (sc >= 90.0) return AppTheme.primaryGreen;
    if (sc >= 75.0) return const Color(0xFFD97706); // Amber
    return AppTheme.error;
  }

  @override
  Widget build(BuildContext context) {
    final effectiveScore = profile?.overallReliabilityScore ?? score ?? 95.0;
    final effectiveTier = profile?.trustTier ?? trustTier ?? context.tr('trust_tier_good_standing');
    final effectiveBadges = profile?.trustBadges ?? badges ?? [];
    final tierColor = _getTierColor(effectiveScore);

    if (compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: tierColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(color: tierColor.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.verified_user_rounded, size: 14, color: tierColor),
            const SizedBox(width: 4),
            Text(
              profile != null && !profile!.hasSufficientHistory
                  ? effectiveTier
                  : '${effectiveScore.toStringAsFixed(0)}% • $effectiveTier',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: tierColor,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: tierColor.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.shield_outlined, color: tierColor, size: 20),
                  ),
                  const SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.tr('reliability_score_label'),
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      Text(
                        effectiveTier,
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: tierColor,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              if (profile == null || profile!.hasSufficientHistory)
                Text(
                  '${effectiveScore.toStringAsFixed(0)}%',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: tierColor,
                  ),
                ),
            ],
          ),
          if (effectiveBadges.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: effectiveBadges.map((badge) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                    border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.2)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.check_circle_outline, size: 12, color: AppTheme.primaryGreen),
                      const SizedBox(width: 4),
                      Text(
                        badge,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.primaryGreen,
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
          if (profile != null && profile!.dimensions.isNotEmpty) ...[
            const Divider(height: 24),
            ...profile!.dimensions.map((dim) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(dim.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        Text('${dim.score.toStringAsFixed(0)}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: (dim.score / 100.0).clamp(0.0, 1.0),
                        minHeight: 5,
                        backgroundColor: AppTheme.background,
                        valueColor: AlwaysStoppedAnimation<Color>(tierColor),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}
