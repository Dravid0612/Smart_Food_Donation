import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../core/utils/food_rescue_status_helper.dart';
import '../models/donation_model.dart';
import 'urgency_badge.dart';
import 'trust_badge.dart';
import 'rescue_ring.dart';

/// Reusable Card component for displaying food donation in feeds and lists.
/// Redesigned with strict semantic separation of:
/// 1. Visual Condition (Good / Fair / Concerning / Uncertain)
/// 2. Rescue Urgency (Fresh / Approaching / Urgent / Critical / Rescue Window Ended)
/// 3. Rescue Window (Remaining time countdown)
/// 4. Feasibility (Rescue Feasible / At Risk / Unlikely / Window Ended)
class DonationCard extends StatelessWidget {
  final DonationModel? donation;
  final String? currentRole;
  final String? foodName;
  final String? category;
  final double? quantity;
  final String? quantityUnit;
  final String? condition;
  final double? confidence;
  final String? urgencyLevel;
  final String? timeRemainingText;
  final String? locationText;
  final String? status;
  final String? storageMethod;
  final String? preparationTime;
  final double? storageDurationHours;
  final String? feasibilityStatus;
  final bool? isFeasible;
  final String? donorTrustLabel;
  final double? donorTrustScore;
  final bool isVerifiedDonor;
  final VoidCallback? onTap;
  final Widget? trailingAction;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final String? acceptLabel;
  final String? rejectLabel;
  final bool isLoading;
  final bool isDisabled;

  const DonationCard({
    super.key,
    this.donation,
    this.currentRole,
    this.foodName,
    this.category,
    this.quantity,
    this.quantityUnit,
    this.condition,
    this.confidence,
    this.urgencyLevel,
    this.timeRemainingText,
    this.locationText,
    this.status,
    this.storageMethod,
    this.preparationTime,
    this.storageDurationHours,
    this.feasibilityStatus,
    this.isFeasible,
    this.donorTrustLabel,
    this.donorTrustScore,
    this.isVerifiedDonor = false,
    this.onTap,
    this.trailingAction,
    this.onAccept,
    this.onReject,
    this.acceptLabel,
    this.rejectLabel,
    this.isLoading = false,
    this.isDisabled = false,
  });

  String _formatPrepAndStorage(BuildContext context, String? prepTime, String? storage, double? storageHours) {
    final parts = <String>[];
    if (prepTime != null && prepTime.isNotEmpty) {
      final dt = DateTime.tryParse(prepTime);
      if (dt != null) {
        final hoursAgo = DateTime.now().difference(dt).inHours;
        if (hoursAgo > 0) {
          parts.add('Prepared ${hoursAgo}h ago');
        } else {
          final minsAgo = DateTime.now().difference(dt).inMinutes;
          parts.add('Prepared ${minsAgo > 0 ? minsAgo : 1}m ago');
        }
      }
    } else if (storageHours != null && storageHours > 0) {
      parts.add('Stored ${storageHours.toInt()}h');
    }

    if (storage != null && storage.isNotEmpty) {
      parts.add(context.trStorage(storage));
    }

    return parts.join(' • ');
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
            child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primaryGreen),
          ),
        ),
      );
    }

    final rawFoodName = foodName ?? donation?.foodName ?? 'Food Donation';
    final effectiveFoodName = context.trFood(rawFoodName);
    final rawCategory = category ?? donation?.foodCategory ?? 'Cooked Food';
    final effectiveCategory = context.trCategory(rawCategory);
    final effectiveQuantity = quantity ?? donation?.quantity ?? 10.0;
    final rawUnit = quantityUnit ?? donation?.quantityUnit ?? 'Meals';
    final effectiveUnit = context.trUnit(rawUnit);
    final effectiveStatus = status ?? donation?.status ?? 'pending';
    final effectiveCondition = condition ?? donation?.aiVisualCondition ?? 'GOOD';
    final effectiveConfidence = confidence ?? donation?.aiConfidenceScore;
    final effectiveUrgency = urgencyLevel ?? donation?.urgencyLevel ?? 'Fresh';
    final effectiveLocation = locationText ?? donation?.pickupAddress ?? '';
    final effectiveStorage = storageMethod ?? donation?.storageMethod;
    final effectivePrepTime = preparationTime ?? donation?.preparationTime;
    final effectiveStorageHours = storageDurationHours ?? donation?.storageDurationHours;
    final effectiveDonorTrustLabel = donorTrustLabel ??
        (donation?.donorName != null ? context.tr('verified_partner') : context.tr('role_donor'));

    // Remaining rescue window minutes
    final remainingMinutes = donation?.remainingMinutes ??
        FoodRescueStatusHelper.calculateRemainingMinutes(donation?.expiryTime);

    // Helpers
    final visualInfo = FoodRescueStatusHelper.getVisualCondition(
      context,
      effectiveCondition,
      confidence: effectiveConfidence,
    );
    final urgencyInfo = FoodRescueStatusHelper.getRescueUrgency(
      context,
      effectiveUrgency,
      remainingMinutes: remainingMinutes,
    );
    final rescueWindowInfo = FoodRescueStatusHelper.getRescueWindow(
      context,
      remainingMinutes,
      urgencyOverride: effectiveUrgency,
    );
    final feasibilityInfo = FoodRescueStatusHelper.getRescueFeasibility(
      context,
      rawFeasibility: feasibilityStatus ?? donation?.feasibilityStatus,
      isFeasible: isFeasible ?? donation?.feasibility?.isFeasible,
      remainingMinutes: remainingMinutes,
    );

    final prepAndStorageText = _formatPrepAndStorage(
      context,
      effectivePrepTime,
      effectiveStorage,
      effectiveStorageHours,
    );

    final canAccept = feasibilityInfo.canAcceptDonation &&
        !rescueWindowInfo.isWindowEnded &&
        effectiveStatus.toLowerCase() == 'pending';

    return Opacity(
      opacity: isDisabled ? 0.6 : 1.0,
      child: Container(
        margin: const EdgeInsets.only(bottom: AppTheme.space12),
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          border: Border.all(
            color: rescueWindowInfo.isWindowEnded
                ? const Color(0xFFC4432B).withValues(alpha: 0.35)
                : AppTheme.border,
          ),
          boxShadow: AppTheme.shadowCard,
        ),
        child: InkWell(
          onTap: isDisabled ? null : onTap,
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          child: Padding(
            padding: const EdgeInsets.all(AppTheme.space16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── 1. TOP ROW: Category + Rescue Urgency Pill ─────────────────
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.secondaryTerracotta.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                      ),
                      child: Text(
                        effectiveCategory.toUpperCase(),
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.secondaryTerracotta,
                          letterSpacing: 0.4,
                        ),
                      ),
                    ),
                    // Urgency Pill (Red / Orange / Amber / Green)
                    UrgencyBadge(
                      level: urgencyInfo.rawKey,
                      remainingMinutes: remainingMinutes,
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space12),

                // ── 2. FOOD NAME, QUANTITY & RESCUE RING ───────────────────────
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            effectiveFoodName,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '${effectiveQuantity.toInt()} $effectiveUnit',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.primaryGreen,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: AppTheme.space12),
                    RescueRing.compact(
                      remainingMinutes: remainingMinutes,
                      urgencyOverride: effectiveUrgency,
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space12),

                // ── 3. VISUAL CONDITION & RESCUE WINDOW SEPARATED ──────────────
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Column(
                    children: [
                      // Visual Condition Line
                      Row(
                        children: [
                          Icon(visualInfo.icon, size: 15, color: visualInfo.color),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              visualInfo.label,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: visualInfo.color,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),

                      // Rescue Window Time Line
                      Row(
                        children: [
                          Icon(
                            rescueWindowInfo.isWindowEnded
                                ? Icons.cancel_outlined
                                : Icons.schedule_outlined,
                            size: 15,
                            color: rescueWindowInfo.ringColor,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              rescueWindowInfo.isWindowEnded
                                  ? context.tr('rescue_window_ended_desc')
                                  : context.trRemainingMinutes(remainingMinutes),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: rescueWindowInfo.ringColor,
                              ),
                            ),
                          ),
                        ],
                      ),

                      // Storage / Preparation Info (if available)
                      if (prepAndStorageText.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            const Icon(Icons.kitchen_outlined, size: 15, color: AppTheme.textSecondary),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                prepAndStorageText,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.textSecondary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: AppTheme.space10),

                // ── 4. FEASIBILITY & TRUST BADGES ──────────────────────────────
                Row(
                  children: [
                    // Feasibility Pill
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: feasibilityInfo.color.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: feasibilityInfo.color.withValues(alpha: 0.25)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(feasibilityInfo.icon, size: 13, color: feasibilityInfo.color),
                          const SizedBox(width: 4),
                          Text(
                            feasibilityInfo.label,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: feasibilityInfo.color,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(),
                    TrustBadge(
                      label: effectiveDonorTrustLabel,
                      score: donorTrustScore ?? 98.0,
                      isVerified: isVerifiedDonor || (donation?.donorId != null),
                    ),
                  ],
                ),

                if (effectiveLocation.isNotEmpty) ...[
                  const SizedBox(height: AppTheme.space10),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 14, color: AppTheme.textSecondary),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          effectiveLocation,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textSecondary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],

                // ── 5. ACTION BUTTONS / TRAILING ACTIONS ───────────────────────
                if (trailingAction != null) ...[
                  const Divider(color: AppTheme.border, height: AppTheme.space20),
                  trailingAction!,
                ] else if (onAccept != null || onReject != null) ...[
                  const Divider(color: AppTheme.border, height: AppTheme.space20),
                  Row(
                    children: [
                      if (onReject != null)
                        Expanded(
                          child: OutlinedButton(
                            onPressed: isDisabled ? null : onReject,
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size(0, 44),
                              foregroundColor: AppTheme.textSecondary,
                              side: const BorderSide(color: AppTheme.border),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                              ),
                              padding: const EdgeInsets.symmetric(vertical: AppTheme.space12),
                            ),
                            child: Text(
                              rejectLabel ??
                                  ((currentRole == 'ngo' || currentRole == 'volunteer')
                                      ? context.tr('pass')
                                      : context.tr('reject_donation')),
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                        ),
                      if (onReject != null && onAccept != null)
                        const SizedBox(width: AppTheme.space12),
                      if (onAccept != null)
                        Expanded(
                          flex: 2,
                          child: ElevatedButton(
                            onPressed: (isDisabled || !canAccept) ? null : onAccept,
                            style: ElevatedButton.styleFrom(
                              minimumSize: const Size(0, 44),
                              backgroundColor: canAccept ? AppTheme.primaryGreen : Colors.grey.shade400,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                              ),
                              padding: const EdgeInsets.symmetric(vertical: AppTheme.space12),
                            ),
                            child: Text(
                              acceptLabel ??
                                  (rescueWindowInfo.isWindowEnded
                                      ? context.trUrgency('window_ended')
                                      : ((currentRole == 'ngo' || currentRole == 'volunteer')
                                          ? context.tr('accept_rescue')
                                          : context.tr('accept_donation'))),
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
