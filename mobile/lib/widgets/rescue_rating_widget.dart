import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Touch-friendly 5-star rating control with accessible text labels.
class RescueRatingWidget extends StatelessWidget {
  final int rating;
  final ValueChanged<int> onRatingChanged;
  final double starSize;
  final bool readOnly;

  const RescueRatingWidget({
    super.key,
    required this.rating,
    required this.onRatingChanged,
    this.starSize = 36.0,
    this.readOnly = false,
  });

  String _getRatingLabel(BuildContext context, int r) {
    switch (r) {
      case 1:
        return '1 / 5 • ${context.tr('opt_poor')}';
      case 2:
        return '2 / 5 • ${context.tr('opt_needs_improvement')}';
      case 3:
        return '3 / 5 • ${context.tr('opt_acceptable')}';
      case 4:
        return '4 / 5 • ${context.tr('opt_good')}';
      case 5:
      default:
        return '5 / 5 • ${context.tr('trust_tier_highly_reliable')}';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(5, (index) {
            final starNum = index + 1;
            final isFilled = starNum <= rating;
            return GestureDetector(
              onTap: readOnly ? null : () => onRatingChanged(starNum),
              behavior: HitTestBehavior.opaque,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4.0),
                child: AnimatedScale(
                  scale: isFilled ? 1.08 : 1.0,
                  duration: const Duration(milliseconds: 150),
                  child: Icon(
                    isFilled ? Icons.star_rounded : Icons.star_outline_rounded,
                    size: starSize,
                    color: isFilled ? const Color(0xFFF59E0B) : AppTheme.border,
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 6),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: Text(
            _getRatingLabel(context, rating),
            key: ValueKey(rating),
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.textSecondary,
            ),
          ),
        ),
      ],
    );
  }
}
