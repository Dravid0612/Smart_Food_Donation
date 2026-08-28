import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Transparent operational feasibility checklist widget.
/// Replaces opaque composite numbers with clear, visible logistical factors.
class RescueChecklistWidget extends StatelessWidget {
  final bool demandMatched;
  final bool ngoOpen;
  final bool capacityAvailable;
  final bool volunteerTransitFit;
  final String expiryWindow;
  final bool isTightDeadline;

  const RescueChecklistWidget({
    super.key,
    this.demandMatched = true,
    this.ngoOpen = true,
    this.capacityAvailable = true,
    this.volunteerTransitFit = true,
    this.expiryWindow = '4h 30m remaining',
    this.isTightDeadline = false,
  });

  @override
  Widget build(BuildContext context) {
    final allPassed = demandMatched && ngoOpen && capacityAvailable && volunteerTransitFit;

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(
          color: allPassed ? AppTheme.primaryGreen.withValues(alpha: 0.3) : AppTheme.warning.withValues(alpha: 0.4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.tr('rescue_feasibility').toUpperCase(),
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.8,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space4),
                decoration: BoxDecoration(
                  color: allPassed ? AppTheme.success.withValues(alpha: 0.1) : AppTheme.warning.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                ),
                child: Text(
                  allPassed ? context.tr('feas_feasible').toUpperCase() : context.tr('feas_tight').toUpperCase(),
                  style: TextStyle(
                    color: allPassed ? AppTheme.success : AppTheme.warning,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          _buildCheckItem(
            label: '✓ NGO Demand Matched',
            subtitle: demandMatched ? 'Directly matches active food category demand' : 'Category demand neutral',
            isSuccess: demandMatched,
          ),
          _buildCheckItem(
            label: '✓ NGO Currently Open',
            subtitle: ngoOpen ? 'NGO facility open and receiving donations' : 'Outside operating hours',
            isSuccess: ngoOpen,
          ),
          _buildCheckItem(
            label: '✓ Receiving Capacity Available',
            subtitle: capacityAvailable ? 'Receiving capacity available and unreserved' : 'Shelter capacity full',
            isSuccess: capacityAvailable,
          ),
          _buildCheckItem(
            label: '✓ Volunteer Transit Fit',
            subtitle: volunteerTransitFit ? 'Batch fits volunteer vehicle payload limit' : 'Payload exceeds volunteer capacity',
            isSuccess: volunteerTransitFit,
          ),
          _buildCheckItem(
            label: '! ${context.tr('expiry_time')}',
            subtitle: expiryWindow,
            isSuccess: !isTightDeadline,
            isWarning: isTightDeadline,
          ),
        ],
      ),
    );
  }

  Widget _buildCheckItem({
    required String label,
    required String subtitle,
    required bool isSuccess,
    bool isWarning = false,
  }) {
    Color iconColor;
    IconData iconData;

    if (isSuccess && !isWarning) {
      iconColor = AppTheme.success;
      iconData = Icons.check_circle_outline;
    } else if (isWarning) {
      iconColor = AppTheme.warning;
      iconData = Icons.access_time;
    } else {
      iconColor = AppTheme.disabled;
      iconData = Icons.radio_button_unchecked;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppTheme.space4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(iconData, color: iconColor, size: 18),
          const SizedBox(width: AppTheme.space8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
