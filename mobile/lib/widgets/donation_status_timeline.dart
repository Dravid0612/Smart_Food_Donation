import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Reusable vertical timeline reflecting the exact 6-state MVP donation lifecycle:
/// Created -> NGO Accepted -> Volunteer Assigned -> Picked Up -> Delivered -> Completed
/// Terminal states: Cancelled, Expired
class DonationStatusTimeline extends StatelessWidget {
  final String status;
  final String? failureReason;
  final DateTime? createdAt;
  final DateTime? acceptedAt;
  final DateTime? collectedAt;
  final DateTime? deliveredAt;

  const DonationStatusTimeline({
    super.key,
    required this.status,
    this.failureReason,
    this.createdAt,
    this.acceptedAt,
    this.collectedAt,
    this.deliveredAt,
  });

  int _getCurrentStepIndex(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return 0;
      case 'accepted':
        return 1;
      case 'volunteer_assigned':
        return 2;
      case 'collected':
        return 3;
      case 'delivered':
        return 4;
      case 'completed':
        return 5;
      case 'cancelled':
      case 'expired':
      case 'rejected':
      case 'pickup_failed':
      case 'delivery_failed':
        return -1; // Terminal / Exception
      default:
        return 0;
    }
  }

  @override
  Widget build(BuildContext context) {
    final normStatus = status.toLowerCase();
    final isTerminal = ['cancelled', 'expired', 'rejected', 'pickup_failed', 'delivery_failed'].contains(normStatus);
    final currentIndex = _getCurrentStepIndex(normStatus);

    final steps = [
      {'title': 'Donation Created', 'sub': 'Surplus food posted with AI assessment'},
      {'title': 'NGO Accepted', 'sub': 'Receiving capacity reserved with concurrency lock'},
      {'title': 'Volunteer Assigned', 'sub': 'Courier transit matched to vehicle capacity'},
      {'title': 'Food Picked Up', 'sub': 'OTP / QR handover verified at donor location'},
      {'title': 'Food Delivered', 'sub': 'Safe transit completed to NGO facility'},
      {'title': 'Completed & Distributed', 'sub': 'Beneficiary distribution logged & verified'},
    ];

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Rescue Timeline',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              if (isTerminal)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space4),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                  ),
                  child: Text(
                    normStatus.toUpperCase(),
                    style: const TextStyle(
                      color: AppTheme.error,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppTheme.space16),
          if (isTerminal && failureReason != null && failureReason!.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(bottom: AppTheme.space16),
              padding: const EdgeInsets.all(AppTheme.space12),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: AppTheme.error, size: 20),
                  const SizedBox(width: AppTheme.space8),
                  Expanded(
                    child: Text(
                      'Terminal status: $failureReason',
                      style: const TextStyle(color: AppTheme.error, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ...List.generate(steps.length, (index) {
            final isCompleted = !isTerminal && index < currentIndex;
            final isCurrent = !isTerminal && index == currentIndex;
            final isPending = isTerminal || index > currentIndex;
            final isLast = index == steps.length - 1;

            Color nodeColor;
            Widget iconWidget;

            if (isCompleted) {
              nodeColor = AppTheme.success;
              iconWidget = const Icon(Icons.check, size: 14, color: Colors.white);
            } else if (isCurrent) {
              nodeColor = AppTheme.secondaryTerracotta;
              iconWidget = Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
              );
            } else {
              nodeColor = AppTheme.disabled;
              iconWidget = Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: AppTheme.disabled.withValues(alpha: 0.6),
                  shape: BoxShape.circle,
                ),
              );
            }

            return IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          color: nodeColor,
                          shape: BoxShape.circle,
                        ),
                        child: Center(child: iconWidget),
                      ),
                      if (!isLast)
                        Expanded(
                          child: Container(
                            width: 2,
                            color: isCompleted ? AppTheme.success : AppTheme.border,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(width: AppTheme.space12),
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(bottom: isLast ? 0 : AppTheme.space16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            steps[index]['title']!,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: isCurrent ? FontWeight.bold : FontWeight.w600,
                              color: isPending ? AppTheme.textSecondary : AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            steps[index]['sub']!,
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
