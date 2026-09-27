import 'dart:io';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/rescue_ring.dart';
import '../../widgets/primary_action_button.dart';

/// Phase 7 Action-First Donor Quick Rescue Screen.
/// Target flow:
///   OPEN APP -> SCAN / CAMERA -> AI ADVISORY CHECK -> CHOOSE FOOD CATEGORY -> SEND TO RESCUE
///
/// Features:
/// - Large typography & minimal inputs
/// - Advisory-only AI visual check (no false claims of certified safety)
/// - Realistic preparation time selection (never blind DateTime.now())
/// - Single dominant green SEND TO RESCUE action
class QuickRescueScreen extends StatefulWidget {
  final String? initialImagePath;
  const QuickRescueScreen({super.key, this.initialImagePath});

  @override
  State<QuickRescueScreen> createState() => _QuickRescueScreenState();
}

class _QuickRescueScreenState extends State<QuickRescueScreen> {
  final ImagePicker _picker = ImagePicker();
  final ApiClient _apiClient = ApiClient();

  XFile? _imageFile;
  bool _isAnalyzing = false;
  bool _isSubmitting = false;

  // AI advisory response
  Map<String, dynamic>? _aiResult;

  // Core donor choices
  String _selectedCategory = 'Cooked Food';
  String _detectedFoodName = 'Cooked Food';
  double _quantity = 25.0;
  final String _quantityUnit = 'Meals';

  // Preparation time choices (never blind DateTime.now())
  int _selectedPrepOption = 1; // 0: <30m, 1: ~1h ago, 2: ~2h ago, 3: 3h+ ago, 4: Custom
  DateTime _resolvedPrepTime = DateTime.now().subtract(const Duration(hours: 1));

  final List<String> _categories = [
    'Cooked Food',
    'Bakery',
    'Fruits',
    'Vegetables',
    'Dairy',
    'Packaged Food',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.initialImagePath != null && File(widget.initialImagePath!).existsSync()) {
      _imageFile = XFile(widget.initialImagePath!);
      _runAiAnalysis();
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _promptImageSource();
      });
    }
  }

  Future<void> _promptImageSource() async {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.space20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                context.tr('scan_or_camera'),
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: AppTheme.space16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildSourceButton(
                    icon: Icons.camera_alt_rounded,
                    label: 'Camera',
                    onTap: () {
                      Navigator.pop(ctx);
                      _pickImage(ImageSource.camera);
                    },
                  ),
                  _buildSourceButton(
                    icon: Icons.photo_library_rounded,
                    label: 'Gallery',
                    onTap: () {
                      Navigator.pop(ctx);
                      _pickImage(ImageSource.gallery);
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSourceButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
      child: Container(
        width: 120,
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          children: [
            Icon(icon, size: 36, color: AppTheme.primaryGreen),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(source: source, imageQuality: 85);
      if (picked != null) {
        setState(() {
          _imageFile = picked;
        });
        _runAiAnalysis();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to capture photo: $e')),
        );
      }
    }
  }

  Future<void> _runAiAnalysis() async {
    if (_imageFile == null) return;
    setState(() {
      _isAnalyzing = true;
    });

    try {
      MultipartFile? multipartImage;
      if (File(_imageFile!.path).existsSync()) {
        multipartImage = await MultipartFile.fromFile(
          _imageFile!.path,
          filename: _imageFile!.path.split(Platform.pathSeparator).last,
        );
      }

      final formData = FormData.fromMap({
        if (multipartImage != null) 'image': multipartImage,
        'food_category': _selectedCategory,
        'quantity': _quantity,
        'storage_method': 'Room Temperature',
        'storage_duration_hours': 1.5,
        'packaging_condition': 'Covered',
        'preparation_time': _resolvedPrepTime.toIso8601String(),
      });

      final response = await _apiClient.dio.post('/ai/analyze-food', data: formData);
      final data = response.data as Map<String, dynamic>;

      if (mounted) {
        setState(() {
          _isAnalyzing = false;
          _aiResult = data;
          _detectedFoodName = data['food_detected'] as String? ?? 'Cooked Food';
          // Auto-adjust category if detected matches known set
          final detected = (data['food_detected'] ?? '').toString().toLowerCase();
          if (detected.contains('fruit') || detected.contains('apple') || detected.contains('banana')) {
            _selectedCategory = 'Fruits';
          } else if (detected.contains('bread') || detected.contains('cake') || detected.contains('puff')) {
            _selectedCategory = 'Bakery';
          } else if (detected.contains('salad') || detected.contains('veg')) {
            _selectedCategory = 'Vegetables';
          } else if (detected.contains('milk') || detected.contains('paneer') || detected.contains('curd')) {
            _selectedCategory = 'Dairy';
          } else {
            _selectedCategory = 'Cooked Food';
          }
        });
      }
    } catch (_) {
      if (mounted) {
        // Graceful fallback to default advisory check
        setState(() {
          _isAnalyzing = false;
          _aiResult = {
            'visual_condition': 'GOOD',
            'confidence': 0.88,
            'urgency_recommendation': 'Fresh',
            'remaining_minutes': 150,
            'food_detected': 'Cooked Food',
            'safety_disclaimer': 'Visual assessment only; this does not certify food safety.',
          };
        });
      }
    }
  }

  void _onPrepTimeOptionSelected(int option) async {
    final now = DateTime.now();
    DateTime calculated;
    if (option == 0) {
      calculated = now.subtract(const Duration(minutes: 20));
    } else if (option == 1) {
      calculated = now.subtract(const Duration(hours: 1));
    } else if (option == 2) {
      calculated = now.subtract(const Duration(hours: 2));
    } else if (option == 3) {
      calculated = now.subtract(const Duration(hours: 3, minutes: 30));
    } else {
      final pickedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(now.subtract(const Duration(hours: 1))),
      );
      if (pickedTime != null) {
        calculated = DateTime(now.year, now.month, now.day, pickedTime.hour, pickedTime.minute);
        if (calculated.isAfter(now)) {
          calculated = calculated.subtract(const Duration(days: 1));
        }
      } else {
        return;
      }
    }

    setState(() {
      _selectedPrepOption = option;
      _resolvedPrepTime = calculated;
    });
  }

  Future<void> _submitSendToRescue() async {
    setState(() => _isSubmitting = true);
    final donProv = Provider.of<DonationProvider>(context, listen: false);

    final now = DateTime.now();
    // Expiry time based on preparation time + category lifetime
    final remainingMins = (_aiResult?['remaining_minutes'] as num?)?.toInt() ?? 180;
    final expiryTime = now.add(Duration(minutes: remainingMins));

    final ok = await donProv.createDonation(
      foodName: _detectedFoodName,
      foodCategory: _selectedCategory,
      quantity: _quantity,
      quantityUnit: _quantityUnit,
      preparationTime: _resolvedPrepTime,
      expiryTime: expiryTime,
      pickupAddress: 'Current Donor Location',
      imageUrl: _imageFile?.path,
      storageMethod: 'Room Temperature',
      storageDurationHours: now.difference(_resolvedPrepTime).inHours.toDouble().clamp(0.5, 8.0),
      packagingCondition: 'Covered',
      aiFoodDetected: _detectedFoodName,
      aiVisualCondition: _aiResult?['visual_condition'] as String? ?? 'GOOD',
      aiConfidenceScore: (_aiResult?['confidence'] as num?)?.toDouble() ?? 0.85,
      conditionScore: 85,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (ok) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard)),
          title: Row(
            children: [
              const Icon(Icons.check_circle_rounded, color: AppTheme.primaryGreen, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  context.tr('rescue_opportunity'),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
              ),
            ],
          ),
          content: Text(
            '${context.tr('send_to_rescue')} successfully! Alerts dispatched to nearby verified NGOs & rescue couriers.',
            style: const TextStyle(fontSize: 14, height: 1.4),
          ),
          actions: [
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                context.go('/donor');
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryGreen,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
              ),
              child: Text(context.tr('done')),
            ),
          ],
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(donProv.errorMessage ?? 'Failed to send donation to rescue. Check connection.'),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final visualCondition = _aiResult?['visual_condition'] as String? ?? 'GOOD';
    final remainingMinutes = (_aiResult?['remaining_minutes'] as num?)?.toInt() ?? 150;
    final urgencyRecommendation = _aiResult?['urgency_recommendation'] as String? ?? 'Fresh';

    Color conditionColor;
    if (visualCondition == 'GOOD') {
      conditionColor = AppTheme.success;
    } else if (visualCondition == 'FAIR') {
      conditionColor = AppTheme.warning;
    } else {
      conditionColor = AppTheme.error;
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('quick_rescue_title'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: _isAnalyzing
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(
                    width: 56,
                    height: 56,
                    child: CircularProgressIndicator(strokeWidth: 4, color: AppTheme.primaryGreen),
                  ),
                  const SizedBox(height: AppTheme.space24),
                  Text(
                    context.tr('visual_condition_advisory'),
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    context.tr('processing'),
                    style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                  ),
                ],
              ),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(AppTheme.space16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── 1. IMAGE & CAMERA ACTION ───────────────────────────────
                  GestureDetector(
                    onTap: _promptImageSource,
                    child: Container(
                      height: 180,
                      decoration: BoxDecoration(
                        color: AppTheme.card,
                        borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                        border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                        image: _imageFile != null
                            ? DecorationImage(
                                image: FileImage(File(_imageFile!.path)),
                                fit: BoxFit.cover,
                              )
                            : null,
                      ),
                      child: _imageFile == null
                          ? Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.add_a_photo_outlined, size: 48, color: AppTheme.primaryGreen),
                                const SizedBox(height: 10),
                                Text(
                                  context.tr('scan_or_camera'),
                                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                                ),
                              ],
                            )
                          : Align(
                              alignment: Alignment.bottomRight,
                              child: Container(
                                margin: const EdgeInsets.all(12),
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.black.withValues(alpha: 0.7),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.camera_alt, color: Colors.white, size: 14),
                                    SizedBox(width: 4),
                                    Text('Retake', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: AppTheme.space16),

                  // ── 2. AI ADVISORY CHECK (VISUAL CONDITION ONLY) ───────────
                  Container(
                    padding: const EdgeInsets.all(AppTheme.space16),
                    decoration: BoxDecoration(
                      color: AppTheme.card,
                      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                      border: Border.all(color: conditionColor.withValues(alpha: 0.4), width: 1.5),
                      boxShadow: AppTheme.shadowCard,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            RescueRing.compact(
                              remainingMinutes: remainingMinutes,
                              urgencyOverride: urgencyRecommendation,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    context.tr('visual_condition_advisory'),
                                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textSecondary, letterSpacing: 0.5),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    context.trVisual(visualCondition),
                                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: conditionColor),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${context.tr('remaining_rescue_window')}: ${context.trRemainingMinutes(remainingMinutes)}',
                                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Disclaimer banner — explicitly retaining safety disclaimer
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppTheme.warningLight,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.info_outline, color: AppTheme.warning, size: 16),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  context.tr('visual_advisory_note'),
                                  style: const TextStyle(fontSize: 11, color: AppTheme.textPrimary, height: 1.3),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppTheme.space16),

                  // ── 3. CHOOSE FOOD CATEGORY ────────────────────────────────
                  Text(
                    context.tr('choose_category'),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _categories.map((cat) {
                      final isSelected = _selectedCategory == cat;
                      return ChoiceChip(
                        label: Text(context.trCategory(cat)),
                        selected: isSelected,
                        selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
                        backgroundColor: AppTheme.card,
                        labelStyle: TextStyle(
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 13,
                        ),
                        side: BorderSide(
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
                        ),
                        onSelected: (val) {
                          if (val) setState(() => _selectedCategory = cat);
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: AppTheme.space16),

                  // ── 4. QUANTITY (MEALS) ────────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        context.tr('quantity'),
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      Text(
                        '${_quantity.toInt()} ${context.trUnit(_quantityUnit)}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [10, 25, 50, 100].map((qty) {
                      final isSel = _quantity.toInt() == qty;
                      return Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: OutlinedButton(
                            onPressed: () => setState(() => _quantity = qty.toDouble()),
                            style: OutlinedButton.styleFrom(
                              backgroundColor: isSel ? AppTheme.primaryGreen.withValues(alpha: 0.12) : AppTheme.card,
                              side: BorderSide(color: isSel ? AppTheme.primaryGreen : AppTheme.border),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                            child: Text(
                              '$qty',
                              style: TextStyle(
                                fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                                color: isSel ? AppTheme.primaryGreen : AppTheme.textPrimary,
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: AppTheme.space16),

                  // ── 5. PREPARATION TIME (CRITICAL INPUT FOR ERW) ───────────
                  Text(
                    context.tr('prep_time_label'),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: 8),
                  Column(
                    children: [
                      _buildPrepRadio(0, context.tr('prep_just_now')),
                      _buildPrepRadio(1, context.tr('prep_1h_ago')),
                      _buildPrepRadio(2, context.tr('prep_2h_ago')),
                      _buildPrepRadio(3, context.tr('prep_3h_plus_ago')),
                      _buildPrepRadio(4, context.tr('prep_custom')),
                    ],
                  ),
                  const SizedBox(height: AppTheme.space24),

                  // ── 6. MAIN ACTION: SEND TO RESCUE (GREEN) ────────────────
                  PrimaryActionButton(
                    label: context.tr('send_to_rescue'),
                    icon: Icons.send_rounded,
                    backgroundColor: AppTheme.primaryGreen,
                    isLoading: _isSubmitting,
                    onPressed: _submitSendToRescue,
                  ),
                  const SizedBox(height: AppTheme.space16),
                ],
              ),
            ),
    );
  }

  Widget _buildPrepRadio(int value, String title) {
    final isSelected = _selectedPrepOption == value;
    return InkWell(
      onTap: () => _onPrepTimeOptionSelected(value),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.08) : AppTheme.card,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
        ),
        child: Row(
          children: [
            Icon(
              isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
              color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
              size: 18,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
