import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../models/feedback_model.dart';
import '../providers/donation_provider.dart';
import 'rescue_rating_widget.dart';
import 'report_problem_dialog.dart';
import 'primary_action_button.dart';

/// Role-Tailored Operational Feedback Dialog.
/// Collects structured dimensions according to participant role (Donor, NGO, Volunteer).
class RescueFeedbackDialog extends StatefulWidget {
  final int donationId;
  final String authorRole; // donor, ngo, volunteer

  const RescueFeedbackDialog({
    super.key,
    required this.donationId,
    required this.authorRole,
  });

  @override
  State<RescueFeedbackDialog> createState() => _RescueFeedbackDialogState();
}

class _RescueFeedbackDialogState extends State<RescueFeedbackDialog> {
  int _overallRating = 5;
  final TextEditingController _commentController = TextEditingController();
  bool _isSubmitting = false;

  // Donor fields
  String _pickupTimeliness = 'On Time';
  String _handoverExperience = 'Smooth';
  String _communicationQuality = 'Clear';
  String _appExperience = 'Helpful';

  // NGO fields
  String _foodConditionRating = 'Good';
  String _quantityAccuracy = 'Accurate';
  String _packagingQuality = 'Good';
  String _volunteerPunctuality = 'On Time';
  String _volunteerProfessionalism = 'Professional';

  // Volunteer fields
  String _donorReadiness = 'Ready';
  String _pickupLocationClarity = 'Easy to Find';
  String _packagingReadiness = 'Well Packaged';
  String _ngoReceivingReadiness = 'Ready to Receive';

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);
    final prov = Provider.of<DonationProvider>(context, listen: false);

    RescueFeedbackModel feedback;

    if (widget.authorRole == 'donor') {
      feedback = RescueFeedbackModel(
        id: 0,
        donationId: widget.donationId,
        authorId: 0,
        authorRole: 'donor',
        overallRating: _overallRating,
        pickupTimeliness: _pickupTimeliness,
        handoverExperience: _handoverExperience,
        communicationQuality: _communicationQuality,
        appExperience: _appExperience,
        comment: _commentController.text.trim().isNotEmpty ? _commentController.text.trim() : null,
        createdAt: DateTime.now(),
      );
    } else if (widget.authorRole == 'ngo') {
      feedback = RescueFeedbackModel(
        id: 0,
        donationId: widget.donationId,
        authorId: 0,
        authorRole: 'ngo',
        overallRating: _overallRating,
        foodConditionRating: _foodConditionRating,
        quantityAccuracy: _quantityAccuracy,
        packagingQuality: _packagingQuality,
        volunteerPunctuality: _volunteerPunctuality,
        volunteerProfessionalism: _volunteerProfessionalism,
        comment: _commentController.text.trim().isNotEmpty ? _commentController.text.trim() : null,
        createdAt: DateTime.now(),
      );
    } else {
      // volunteer
      feedback = RescueFeedbackModel(
        id: 0,
        donationId: widget.donationId,
        authorId: 0,
        authorRole: 'volunteer',
        overallRating: _overallRating,
        donorReadiness: _donorReadiness,
        pickupLocationClarity: _pickupLocationClarity,
        packagingReadiness: _packagingReadiness,
        ngoReceivingReadiness: _ngoReceivingReadiness,
        comment: _commentController.text.trim().isNotEmpty ? _commentController.text.trim() : null,
        createdAt: DateTime.now(),
      );
    }

    final success = await prov.submitRescueFeedback(widget.donationId, feedback);

    setState(() => _isSubmitting = false);

    if (mounted) {
      Navigator.of(context).pop(success);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? context.tr('feedback_submitted_success') : context.tr('err_server')),
          backgroundColor: success ? AppTheme.primaryGreen : AppTheme.error,
        ),
      );
    }
  }

  Widget _buildChoiceRow({
    required String question,
    required String selectedValue,
    required List<String> options,
    required ValueChanged<String> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: options.map((opt) {
              final isSel = selectedValue == opt;
              return ChoiceChip(
                label: Text(
                  opt,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                    color: isSel ? Colors.white : AppTheme.textPrimary,
                  ),
                ),
                selected: isSel,
                selectedColor: AppTheme.primaryGreen,
                backgroundColor: AppTheme.background,
                onSelected: (_) => onChanged(opt),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.card,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryGreen.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.star_outline_rounded, color: AppTheme.primaryGreen, size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('rate_rescue_experience'),
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Donation #${widget.donationId}',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () => Navigator.of(context).pop(false),
                  ),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              Text(
                context.tr('how_was_rescue'),
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              RescueRatingWidget(
                rating: _overallRating,
                onRatingChanged: (val) => setState(() => _overallRating = val),
              ),
              const SizedBox(height: AppTheme.space16),
              const Divider(),
              const SizedBox(height: AppTheme.space12),

              // Role-tailored questions
              if (widget.authorRole == 'donor') ...[
                _buildChoiceRow(
                  question: context.tr('pickup_timeliness_q'),
                  selectedValue: _pickupTimeliness,
                  options: [context.tr('opt_on_time'), context.tr('opt_slight_delay'), context.tr('opt_late')],
                  onChanged: (v) => setState(() => _pickupTimeliness = v),
                ),
                _buildChoiceRow(
                  question: context.tr('handover_experience_q'),
                  selectedValue: _handoverExperience,
                  options: [context.tr('opt_smooth'), context.tr('opt_acceptable'), context.tr('opt_difficult')],
                  onChanged: (v) => setState(() => _handoverExperience = v),
                ),
                _buildChoiceRow(
                  question: context.tr('communication_quality_q'),
                  selectedValue: _communicationQuality,
                  options: [context.tr('opt_clear'), context.tr('opt_acceptable'), context.tr('opt_poor')],
                  onChanged: (v) => setState(() => _communicationQuality = v),
                ),
                _buildChoiceRow(
                  question: context.tr('app_experience_q'),
                  selectedValue: _appExperience,
                  options: [context.tr('opt_helpful'), context.tr('opt_acceptable'), context.tr('opt_needs_improvement')],
                  onChanged: (v) => setState(() => _appExperience = v),
                ),
              ] else if (widget.authorRole == 'ngo') ...[
                _buildChoiceRow(
                  question: context.tr('food_condition_q'),
                  selectedValue: _foodConditionRating,
                  options: [context.tr('opt_good'), context.tr('opt_acceptable'), context.tr('opt_damaged')],
                  onChanged: (v) => setState(() => _foodConditionRating = v),
                ),
                _buildChoiceRow(
                  question: context.tr('quantity_accuracy_q'),
                  selectedValue: _quantityAccuracy,
                  options: [context.tr('opt_accurate'), context.tr('opt_minor_diff'), context.tr('opt_major_diff')],
                  onChanged: (v) => setState(() => _quantityAccuracy = v),
                ),
                _buildChoiceRow(
                  question: context.tr('packaging_quality_q'),
                  selectedValue: _packagingQuality,
                  options: [context.tr('opt_good'), context.tr('opt_acceptable'), context.tr('opt_poor')],
                  onChanged: (v) => setState(() => _packagingQuality = v),
                ),
                _buildChoiceRow(
                  question: context.tr('volunteer_punctuality_q'),
                  selectedValue: _volunteerPunctuality,
                  options: [context.tr('opt_on_time'), context.tr('opt_slightly_late'), context.tr('opt_very_late')],
                  onChanged: (v) => setState(() => _volunteerPunctuality = v),
                ),
                _buildChoiceRow(
                  question: context.tr('volunteer_professionalism_q'),
                  selectedValue: _volunteerProfessionalism,
                  options: [context.tr('opt_professional'), context.tr('opt_acceptable'), context.tr('opt_unprofessional')],
                  onChanged: (v) => setState(() => _volunteerProfessionalism = v),
                ),
              ] else ...[
                // Volunteer
                _buildChoiceRow(
                  question: context.tr('donor_readiness_q'),
                  selectedValue: _donorReadiness,
                  options: [context.tr('opt_ready'), context.tr('opt_partially_ready'), context.tr('opt_not_ready')],
                  onChanged: (v) => setState(() => _donorReadiness = v),
                ),
                _buildChoiceRow(
                  question: context.tr('pickup_location_clarity_q'),
                  selectedValue: _pickupLocationClarity,
                  options: [context.tr('opt_easy_to_find'), context.tr('opt_some_difficulty'), context.tr('opt_hard_to_find')],
                  onChanged: (v) => setState(() => _pickupLocationClarity = v),
                ),
                _buildChoiceRow(
                  question: context.tr('packaging_readiness_q'),
                  selectedValue: _packagingReadiness,
                  options: [context.tr('opt_well_packaged'), context.tr('opt_partially_prepared'), context.tr('opt_poorly_packaged')],
                  onChanged: (v) => setState(() => _packagingReadiness = v),
                ),
                _buildChoiceRow(
                  question: context.tr('ngo_receiving_readiness_q'),
                  selectedValue: _ngoReceivingReadiness,
                  options: [context.tr('opt_ready_to_receive'), context.tr('opt_minor_wait'), context.tr('opt_unprepared')],
                  onChanged: (v) => setState(() => _ngoReceivingReadiness = v),
                ),
              ],

              // Optional Comment
              TextField(
                controller: _commentController,
                maxLines: 2,
                decoration: InputDecoration(
                  hintText: context.tr('optional_comment_hint'),
                  hintStyle: const TextStyle(fontSize: 12),
                  filled: true,
                  fillColor: AppTheme.background,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              PrimaryActionButton(
                label: context.tr('submit_feedback').toUpperCase(),
                backgroundColor: AppTheme.primaryGreen,
                isLoading: _isSubmitting,
                onPressed: _submit,
              ),
              const SizedBox(height: 10),

              // Problem shortcut
              TextButton.icon(
                onPressed: () {
                  Navigator.of(context).pop();
                  showDialog(
                    context: context,
                    builder: (ctx) => ReportProblemDialog(
                      donationId: widget.donationId,
                      currentRole: widget.authorRole,
                    ),
                  );
                },
                icon: const Icon(Icons.report_problem_outlined, size: 16, color: AppTheme.secondaryTerracotta),
                label: Text(
                  context.tr('report_problem'),
                  style: const TextStyle(fontSize: 12, color: AppTheme.secondaryTerracotta, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
