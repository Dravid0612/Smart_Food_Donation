import 'dart:io';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/rescue_ring.dart';

/// Production AI Food Condition Analysis Screen.
/// Performs multi-feature vision analysis and donor metadata decision fusion via the backend API.
/// Adheres strictly to the unified Humanitarian Logistics Design System.
class DonorAiAnalysisScreen extends StatefulWidget {
  final String? imagePath;
  const DonorAiAnalysisScreen({super.key, this.imagePath});

  @override
  State<DonorAiAnalysisScreen> createState() => _DonorAiAnalysisScreenState();
}

class _DonorAiAnalysisScreenState extends State<DonorAiAnalysisScreen>
    with TickerProviderStateMixin {
  final ApiClient _apiClient = ApiClient();

  bool _analyzing = true;
  String? _errorMessage;
  late AnimationController _pulseController;
  Map<String, dynamic>? _results;

  // Metadata inputs for decision fusion
  final String _foodCategory = 'Cooked Food';
  final double _quantity = 25.0;
  String _storageMethod = 'Room Temperature';
  final double _storageDurationHours = 2.0;
  String _packagingCondition = 'Sealed / Covered';

  final List<String> _analysisSteps = [
    'Sending image to vision backend...',
    'Scanning color & discoloration patterns...',
    'Detecting surface texture & visible spoilage...',
    'Inspecting packaging integrity...',
    'Fusing metadata (storage & temperature)...',
    'Generating structured assessment...',
  ];
  int _currentStep = 0;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);

    _runRealAnalysis();
  }

  Future<void> _runRealAnalysis() async {
    setState(() {
      _analyzing = true;
      _errorMessage = null;
      _currentStep = 0;
    });

    // Step animation ticker
    for (int i = 0; i < 4; i++) {
      await Future.delayed(const Duration(milliseconds: 350));
      if (mounted) setState(() => _currentStep = i);
    }

    try {
      MultipartFile? multipartImage;
      if (widget.imagePath != null && File(widget.imagePath!).existsSync()) {
        multipartImage = await MultipartFile.fromFile(
          widget.imagePath!,
          filename: widget.imagePath!.split(Platform.pathSeparator).last,
        );
      }

      final formData = FormData.fromMap({
        if (multipartImage != null) 'image': multipartImage,
        'food_category': _foodCategory,
        'quantity': _quantity,
        'storage_method': _storageMethod,
        'storage_duration_hours': _storageDurationHours,
        'packaging_condition': _packagingCondition,
      });

      final response = await _apiClient.dio.post(
        '/ai/analyze-food',
        data: formData,
      );

      if (mounted) setState(() => _currentStep = 5);
      await Future.delayed(const Duration(milliseconds: 300));

      if (mounted) {
        setState(() {
          _analyzing = false;
          _results = response.data as Map<String, dynamic>;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _analyzing = false;
          _errorMessage = 'Analysis error: Unable to connect to AI vision service.';
        });
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('ai_vision_analysis'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Image Preview Card
            Container(
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                border: Border.all(color: AppTheme.border),
                boxShadow: AppTheme.shadowCard,
              ),
              clipBehavior: Clip.antiAlias,
              child: widget.imagePath != null && File(widget.imagePath!).existsSync()
                  ? Image.file(
                      File(widget.imagePath!),
                      height: 200,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    )
                  : Container(
                      height: 160,
                      color: AppTheme.borderLight,
                      child: const Center(
                        child: Icon(Icons.restaurant, color: AppTheme.textMuted, size: 48),
                      ),
                    ),
            ),
            const SizedBox(height: AppTheme.space16),

            // Metadata Tuning Card
            _buildMetadataInputCard(),
            const SizedBox(height: AppTheme.space16),

            if (_analyzing)
              _buildAnalyzingView()
            else if (_errorMessage != null)
              _buildErrorView()
            else if (_results != null)
              _buildResultsView(),
          ],
        ),
      ),
    );
  }

  Widget _buildMetadataInputCard() {
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
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(Icons.tune, color: AppTheme.primaryGreen, size: 16),
              ),
              const SizedBox(width: 8),
              Text(
                context.tr('storage_method'),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space14),
          Row(
            children: [
              Expanded(
                child: _buildDropdown(
                  label: context.tr('storage_method'),
                  value: _storageMethod,
                  items: ['Room Temperature', 'Refrigerated', 'Heated/Insulated', 'Frozen'],
                  onChanged: (v) {
                    if (v != null) {
                      setState(() => _storageMethod = v);
                      _runRealAnalysis();
                    }
                  },
                ),
              ),
              const SizedBox(width: AppTheme.space12),
              Expanded(
                child: _buildDropdown(
                  label: context.tr('packaging_condition'),
                  value: _packagingCondition,
                  items: ['Sealed / Covered', 'Open Container', 'Individual Packets'],
                  onChanged: (v) {
                    if (v != null) {
                      setState(() => _packagingCondition = v);
                      _runRealAnalysis();
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11, fontWeight: FontWeight.w500)),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppTheme.background,
            borderRadius: BorderRadius.circular(AppTheme.radiusButton),
            border: Border.all(color: AppTheme.border),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              dropdownColor: AppTheme.card,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12, fontWeight: FontWeight.w600),
              items: items.map((i) => DropdownMenuItem(value: i, child: Text(i, overflow: TextOverflow.ellipsis))).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAnalyzingView() {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space20),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        children: [
          const SizedBox(
            width: 32,
            height: 32,
            child: CircularProgressIndicator(strokeWidth: 3, color: AppTheme.primaryGreen),
          ),
          const SizedBox(height: AppTheme.space16),
          Text(
            context.tr('processing'),
            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: AppTheme.space16),
          ...List.generate(_analysisSteps.length, (i) {
            final done = i < _currentStep;
            final active = i == _currentStep;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Icon(
                    done ? Icons.check_circle : active ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                    color: done ? AppTheme.primaryGreen : active ? AppTheme.textPrimary : AppTheme.textMuted,
                    size: 16,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _analysisSteps[i],
                      style: TextStyle(
                        color: done ? AppTheme.primaryGreen : active ? AppTheme.textPrimary : AppTheme.textMuted,
                        fontSize: 12,
                        fontWeight: active ? FontWeight.w600 : FontWeight.normal,
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

  Widget _buildErrorView() {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space20),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.error, size: 40),
          const SizedBox(height: AppTheme.space12),
          Text(
            context.trError(_errorMessage ?? 'err_server'),
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppTheme.space16),
          ElevatedButton(
            onPressed: _runRealAnalysis,
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryGreen),
            child: Text(context.tr('retry')),
          ),
        ],
      ),
    );
  }

  Widget _buildResultsView() {
    final r = _results!;
    final visualCondition = r['visual_condition'] as String? ?? 'GOOD';
    final confidence = ((r['confidence'] as num?)?.toDouble() ?? 0.88) * 100;
    Color badgeColor;
    if (visualCondition == 'GOOD') {
      badgeColor = AppTheme.success;
    } else if (visualCondition == 'FAIR') {
      badgeColor = AppTheme.warning;
    } else {
      badgeColor = AppTheme.error;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Overall Condition & Rescue Ring Card
        Container(
          padding: const EdgeInsets.all(AppTheme.space20),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
            border: Border.all(color: badgeColor.withValues(alpha: 0.4), width: 1.5),
            boxShadow: AppTheme.shadowCard,
          ),
          child: Column(
            children: [
              RescueRing.hero(
                remainingMinutes: (r['remaining_minutes'] as num?)?.toInt() ?? 120,
                urgencyOverride: r['urgency_recommendation'] as String? ?? 'Fresh',
              ),
              const SizedBox(height: AppTheme.space14),
              Text(
                '${context.tr('visual_condition')}: ${context.trVisual(visualCondition)}',
                style: TextStyle(color: badgeColor, fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: -0.2),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${context.tr('ai_observation_confidence')}: ${confidence.toStringAsFixed(0)}%',
                      style: const TextStyle(color: AppTheme.primaryGreen, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: badgeColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      context.trUrgency(r['urgency_recommendation'] as String? ?? 'Fresh'),
                      style: TextStyle(color: badgeColor, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        // Structured Breakdown Table
        Text(
          context.tr('ai_vision_analysis'),
          style: const TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: -0.2),
        ),
        const SizedBox(height: AppTheme.space10),
        _buildResultRow(context.tr('food_item'), r['food_detected'] as String? ?? 'Cooked Food', 'pass'),
        _buildResultRow(context.tr('visual_condition'), context.trVisual(r['visual_condition'] as String? ?? 'GOOD'), 'pass'),
        _buildResultRow(context.tr('packaging_condition'), r['packaging'] as String? ?? 'Intact', 'pass'),
        _buildResultRow(context.tr('urgency_level'), context.trUrgency(r['urgency_recommendation'] as String? ?? 'Fresh'), 'pass'),
        const SizedBox(height: AppTheme.space16),

        // Mandatory Disclaimer
        Container(
          padding: const EdgeInsets.all(AppTheme.space14),
          decoration: BoxDecoration(
            color: AppTheme.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
            border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline, color: AppTheme.warning, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  context.trDisclaimer(),
                  style: const TextStyle(color: AppTheme.textPrimary, fontSize: 12, height: 1.35),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space24),

        // Action Buttons
        ElevatedButton(
          onPressed: () {
            context.go('/donor/create', extra: {
              'food_name': r['food_detected'],
              'ai_food_detected': r['food_detected'],
              'ai_visible_spoilage': r['visible_spoilage'],
              'ai_discoloration': r['discoloration'],
              'ai_packaging_intact': r['packaging'],
              'ai_visual_condition': r['visual_condition'],
              'ai_confidence_score': r['confidence'],
              'condition_score': r['condition_score'],
              'storage_method': _storageMethod,
              'storage_duration_hours': _storageDurationHours,
              'packaging_condition': _packagingCondition,
            });
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryGreen,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
          ),
          child: Text('${context.tr('continue_btn')} →', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        ),
        const SizedBox(height: AppTheme.space10),
        OutlinedButton(
          onPressed: () => context.pop(),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppTheme.textSecondary,
            side: const BorderSide(color: AppTheme.border),
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
          ),
          child: Text(context.tr('retry')),
        ),
      ],
    );
  }

  Widget _buildResultRow(String label, String value, String status) {
    Color statusColor = status == 'pass' ? AppTheme.primaryGreen : AppTheme.warning;
    IconData statusIcon = status == 'pass' ? Icons.check_circle_outline : Icons.warning_amber_outlined;

    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space8),
      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space14, vertical: AppTheme.space12),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
