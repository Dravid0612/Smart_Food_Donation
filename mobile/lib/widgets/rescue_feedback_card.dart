import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../models/feedback_model.dart';
import 'rescue_feedback_dialog.dart';
import 'report_problem_dialog.dart';

/// Embedded Completion & Feedback Card for Donation Screens.
class RescueFeedbackCard extends StatelessWidget {
  final int donationId;
  final String currentRole; // donor, ngo, volunteer
  final String donationStatus; // completed, delivered, cancelled, expired, etc.
  final bool hasSubmittedFeedback;
  final RescueFeedbackModel? submittedFeedback;
  final VoidCallback? onFeedbackSubmitted;

  const RescueFeedbackCard({
    super.key,
    required this.donationId,
    required this.currentRole,
    this.donationStatus = 'completed',
    this.hasSubmittedFeedback = false,
    this.submittedFeedback,
    this.onFeedbackSubmitted,
  });

  bool get isFailedOrCancelled =>
      ['cancelled', 'expired', 'pickup_failed', 'failed'].contains(donationStatus.toLowerCase());

  @override
  Widget build(BuildContext context) {
    final isFailed = isFailedOrCancelled;
    final cardColor = isFailed ? const Color(0xFFEF4444) : AppTheme.primaryGreen;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(
          color: hasSubmittedFeedback
              ? cardColor.withValues(alpha: 0.3)
              : cardColor.withValues(alpha: 0.6),
          width: 1.5,
        ),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: cardColor.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  isFailed ? Icons.error_outline_rounded : Icons.check_circle_rounded,
                  color: cardColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isFailed
                          ? (context.tr('feedback_failed_rescue_title'))
                          : context.tr('rescue_complete_banner'),
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: cardColor,
                      ),
                    ),
                    Text(
                      isFailed
                          ? (context.tr('feedback_what_went_wrong'))
                          : context.tr('rate_experience_sub'),
                      style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          if (hasSubmittedFeedback) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(AppTheme.radiusInput),
              ),
              child: Row(
                children: [
                  const Icon(Icons.thumb_up_alt_outlined, color: AppTheme.primaryGreen, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      context.tr('feedback_submitted_success'),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.primaryGreen,
                      ),
                    ),
                  ),
                  if (submittedFeedback != null)
                    Row(
                      children: List.generate(
                        submittedFeedback!.overallRating,
                        (_) => const Icon(Icons.star_rounded, size: 14, color: Color(0xFFF59E0B)),
                      ),
                    ),
                ],
              ),
            ),
          ] else ...[
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryGreen,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                    ),
                    onPressed: () async {
                      final result = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => RescueFeedbackDialog(
                          donationId: donationId,
                          authorRole: currentRole,
                        ),
                      );
                      if (result == true && onFeedbackSubmitted != null) {
                        onFeedbackSubmitted!();
                      }
                    },
                    icon: const Icon(Icons.rate_review_outlined, size: 16),
                    label: Text(
                      context.tr('rate_rescue_experience'),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.secondaryTerracotta,
                    side: const BorderSide(color: AppTheme.secondaryTerracotta),
                    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                  ),
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (ctx) => ReportProblemDialog(
                        donationId: donationId,
                        currentRole: currentRole,
                      ),
                    );
                  },
                  icon: const Icon(Icons.report_problem_outlined, size: 16),
                  label: Text(
                    context.tr('report_problem'),
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
