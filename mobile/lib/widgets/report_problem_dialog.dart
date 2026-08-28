import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../providers/donation_provider.dart';
import 'primary_action_button.dart';

/// Reusable Problem & Incident Reporting Dialog.
/// Handles both standard operational issues and dedicated Food Condition Incident reports.
class ReportProblemDialog extends StatefulWidget {
  final int donationId;
  final String currentRole; // donor, ngo, volunteer
  final bool initialFoodConditionConcern;

  const ReportProblemDialog({
    super.key,
    required this.donationId,
    required this.currentRole,
    this.initialFoodConditionConcern = false,
  });

  @override
  State<ReportProblemDialog> createState() => _ReportProblemDialogState();
}

class _ReportProblemDialogState extends State<ReportProblemDialog> {
  late String _selectedCategory;
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _evidenceUrlController = TextEditingController();
  final TextEditingController _spoilageNotesController = TextEditingController();

  // Food condition incident options
  String _selectedFoodIssue = 'Visible spoilage';
  bool _isSubmitting = false;

  final List<String> _commonCategories = [
    'issue_cat_pickup_not_happened',
    'issue_cat_volunteer_no_show',
    'issue_cat_volunteer_late',
    'issue_cat_donor_unavailable',
    'issue_cat_ngo_unavailable',
    'issue_cat_quantity_mismatch',
    'issue_cat_packaging_damaged',
    'issue_cat_food_condition_concern',
    'issue_cat_location_issue',
    'issue_cat_communication_issue',
    'issue_cat_otp_issue',
    'issue_cat_delivery_issue',
    'issue_cat_distribution_issue',
    'issue_cat_other',
  ];

  @override
  void initState() {
    super.initState();
    _selectedCategory = widget.initialFoodConditionConcern
        ? 'issue_cat_food_condition_concern'
        : _getDefaultCategoryForRole(widget.currentRole);
  }

  String _getDefaultCategoryForRole(String role) {
    if (role == 'donor') return 'issue_cat_volunteer_no_show';
    if (role == 'ngo') return 'issue_cat_quantity_mismatch';
    return 'issue_cat_donor_unavailable';
  }

  String _categoryKeyToBackend(String trKey) {
    return trKey.replaceFirst('issue_cat_', '');
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    _evidenceUrlController.dispose();
    _spoilageNotesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final rawCategory = _categoryKeyToBackend(_selectedCategory);
    final isFoodSafety = rawCategory == 'food_condition_concern';

    final desc = _descriptionController.text.trim();
    if (desc.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.tr('describe_issue_hint')),
          backgroundColor: AppTheme.error,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    final prov = Provider.of<DonationProvider>(context, listen: false);

    final success = await prov.reportRescueIssue(
      donationId: widget.donationId,
      category: rawCategory,
      description: desc,
      isFoodSafetyIncident: isFoodSafety,
      foodSafetyDetails: isFoodSafety ? '$_selectedFoodIssue: ${_spoilageNotesController.text.trim()}' : null,
      evidenceUrl: _evidenceUrlController.text.trim().isNotEmpty ? _evidenceUrlController.text.trim() : null,
    );

    setState(() => _isSubmitting = false);

    if (mounted) {
      Navigator.of(context).pop(success);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? context.tr('issue_submitted_success') : context.tr('err_server')),
          backgroundColor: success ? AppTheme.primaryGreen : AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isFoodSafety = _categoryKeyToBackend(_selectedCategory) == 'food_condition_concern';

    return Dialog(
      backgroundColor: AppTheme.card,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: (isFoodSafety ? AppTheme.error : const Color(0xFFD97706)).withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      isFoodSafety ? Icons.warning_amber_rounded : Icons.report_problem_outlined,
                      color: isFoodSafety ? AppTheme.error : const Color(0xFFD97706),
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isFoodSafety
                              ? context.tr('food_condition_incident_title')
                              : context.tr('report_problem'),
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textPrimary,
                          ),
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

              // Category Selector
              Text(
                context.tr('select_issue_category'),
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                  border: Border.all(color: AppTheme.border),
                  color: AppTheme.background,
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    isExpanded: true,
                    value: _selectedCategory,
                    items: _commonCategories.map((key) {
                      return DropdownMenuItem<String>(
                        value: key,
                        child: Text(
                          context.tr(key),
                          style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                        ),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) setState(() => _selectedCategory = val);
                    },
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              // Food condition incident special workflow
              if (isFoodSafety) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    border: Border.all(color: AppTheme.error.withValues(alpha: 0.25)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.info_outline, color: AppTheme.error, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          context.tr('food_safety_disclaimer_incident'),
                          style: const TextStyle(fontSize: 11, color: AppTheme.textPrimary, height: 1.3),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppTheme.space12),

                Text(
                  context.tr('incident_observed_q'),
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    'incident_spoilage',
                    'incident_damaged_pkg',
                    'incident_temperature',
                    'incident_contamination',
                    'incident_other'
                  ].map((obsKey) {
                    final label = context.tr(obsKey);
                    final isSel = _selectedFoodIssue == label;
                    return ChoiceChip(
                      label: Text(label, style: TextStyle(fontSize: 11, color: isSel ? Colors.white : AppTheme.textPrimary)),
                      selected: isSel,
                      selectedColor: AppTheme.error,
                      backgroundColor: AppTheme.background,
                      onSelected: (_) => setState(() => _selectedFoodIssue = label),
                    );
                  }).toList(),
                ),
                const SizedBox(height: AppTheme.space12),
              ],

              // Description input
              Text(
                context.tr('details'),
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _descriptionController,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: context.tr('describe_issue_hint'),
                  hintStyle: const TextStyle(fontSize: 12),
                  filled: true,
                  fillColor: AppTheme.background,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space12),

              // Evidence photo URL
              TextField(
                controller: _evidenceUrlController,
                decoration: InputDecoration(
                  hintText: context.tr('evidence_photo_hint'),
                  hintStyle: const TextStyle(fontSize: 12),
                  prefixIcon: const Icon(Icons.add_a_photo_outlined, size: 18),
                  filled: true,
                  fillColor: AppTheme.background,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space20),

              PrimaryActionButton(
                label: isFoodSafety
                    ? context.tr('submit_incident_for_review').toUpperCase()
                    : context.tr('submit_issue_report').toUpperCase(),
                backgroundColor: isFoodSafety ? AppTheme.error : AppTheme.secondaryTerracotta,
                isLoading: _isSubmitting,
                onPressed: _submit,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
