import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/donation_model.dart';
import 'rescue_ring.dart';

/// Operational Intervention Card for Admin Dashboard highlighting stuck donations requiring immediate action.
class InterventionCard extends StatelessWidget {
  final DonationModel? donation;
  final int? donationId;
  final String? foodName;
  final String? foodCategory;
  final double? quantity;
  final String? quantityUnit;
  final String? interventionType;
  final String? reason;
  final double? timeRemainingHours;
  final double? foodAtRiskMeals;
  final String? suggestedAction;
  final VoidCallback? onIntervene;
  final VoidCallback? onEscalate;
  final VoidCallback? onReassign;
  final bool isLoading;

  const InterventionCard({
    super.key,
    this.donation,
    this.donationId,
    this.foodName,
    this.foodCategory,
    this.quantity,
    this.quantityUnit,
    this.interventionType,
    this.reason,
    this.timeRemainingHours,
    this.foodAtRiskMeals,
    this.suggestedAction,
    this.onIntervene,
    this.onEscalate,
    this.onReassign,
    this.isLoading = false,
  });

  String _formatType(String type) {
    switch (type) {
      case 'URGENT_NO_NGO':
        return 'URGENT — NO NGO';
      case 'URGENT_NO_VOLUNTEER':
        return 'URGENT — NO VOLUNTEER';
      case 'PICKUP_FAILED':
        return 'PICKUP FAILED';
      case 'DELIVERY_FAILED':
        return 'DELIVERY FAILED';
      case 'DEADLINE_APPROACHING':
        return 'DEADLINE CRITICAL';
      default:
        return type.replaceAll('_', ' ');
    }
  }

  String _determineType(DonationModel d) {
    if (d.status == 'pickup_failed') return 'PICKUP_FAILED';
    if (d.status == 'delivery_failed') return 'DELIVERY_FAILED';
    if (d.status == 'pending') return 'URGENT_NO_NGO';
    if (d.status == 'accepted' && d.assignedVolunteerId == null) return 'URGENT_NO_VOLUNTEER';
    return 'DEADLINE_APPROACHING';
  }

  String _determineReason(DonationModel d) {
    if (d.failureReason != null && d.failureReason!.isNotEmpty) {
      return d.failureReason!;
    }
    if (d.status == 'pending') {
      return 'Posted surplus waiting for verified shelter acceptance in target radius.';
    }
    if (d.status == 'accepted') {
      return 'Accepted by NGO; awaiting active courier transit assignment.';
    }
    return 'Approaching time-to-expiry threshold.';
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Container(
        margin: const EdgeInsets.only(bottom: AppTheme.space12),
        height: 160,
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.warning),
          ),
        ),
      );
    }

    final effectiveId = donationId ?? donation?.id ?? 1;
    final effectiveFoodName = foodName ?? donation?.foodName ?? 'Prepared Food';
    final effectiveCategory = foodCategory ?? donation?.foodCategory ?? 'Cooked Food';
    final effectiveQuantity = quantity ?? donation?.quantity ?? 50.0;
    final effectiveUnit = quantityUnit ?? donation?.quantityUnit ?? 'Meals';
    final effectiveType = interventionType ?? (donation != null ? _determineType(donation!) : 'URGENT_NO_NGO');
    final effectiveReason = reason ?? (donation != null ? _determineReason(donation!) : 'No response from nearby partners.');
    final effectiveHours = timeRemainingHours ?? 1.2;
    final effectiveAtRisk = foodAtRiskMeals ?? effectiveQuantity;
    final effectiveAction = suggestedAction ?? 'Broadcast emergency priority alert and expand courier matching radius.';

    final typeLabel = _formatType(effectiveType);
    final isUrgent = effectiveHours <= 1.5 || effectiveType.contains('URGENT') || effectiveType.contains('FAILED');
    final accentColor = isUrgent ? AppTheme.error : AppTheme.warning;

    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space12),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: accentColor.withValues(alpha: 0.4), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: accentColor.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header alert strip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.1),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(AppTheme.radiusCard - 1),
                topRight: Radius.circular(AppTheme.radiusCard - 1),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.warning_amber_rounded, size: 18, color: accentColor),
                const SizedBox(width: AppTheme.space8),
                Text(
                  typeLabel,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: accentColor,
                    letterSpacing: 0.5,
                  ),
                ),
                const Spacer(),
                Text(
                  '${effectiveHours.toStringAsFixed(1)}h left',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: accentColor,
                  ),
                ),
              ],
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(AppTheme.space16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '#$effectiveId • $effectiveFoodName ($effectiveCategory)',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${effectiveAtRisk.toInt()} $effectiveUnit at risk',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: accentColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    RescueRing.compact(
                      remainingMinutes: (effectiveHours * 60).round(),
                      urgencyOverride: 'critical',
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space8),

                // Issue Reason box
                Container(
                  padding: const EdgeInsets.all(AppTheme.space12),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.info_outline, size: 14, color: AppTheme.textSecondary),
                          const SizedBox(width: AppTheme.space4),
                          const Text('Cause: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                          Expanded(
                            child: Text(
                              effectiveReason,
                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppTheme.space4),
                      Row(
                        children: [
                          const Icon(Icons.lightbulb_outline, size: 14, color: AppTheme.primaryGreen),
                          const SizedBox(width: AppTheme.space4),
                          const Text('Action: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                          Expanded(
                            child: Text(
                              effectiveAction,
                              style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary, fontWeight: FontWeight.w500),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppTheme.space16),

                // Action buttons
                Row(
                  children: [
                    if (onReassign != null) ...[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: onReassign,
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(0, 44),
                            foregroundColor: AppTheme.textPrimary,
                            side: const BorderSide(color: AppTheme.border),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: AppTheme.space12),
                          ),
                          child: const Text('Re-assign', style: TextStyle(fontWeight: FontWeight.w600)),
                        ),
                      ),
                      const SizedBox(width: AppTheme.space8),
                    ],
                    Expanded(
                      flex: 2,
                      child: ElevatedButton.icon(
                        onPressed: onEscalate ?? onIntervene,
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(0, 44),
                          backgroundColor: accentColor,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: AppTheme.space12),
                        ),
                        icon: const Icon(Icons.bolt, size: 18),
                        label: const Text('Execute Escalation', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
