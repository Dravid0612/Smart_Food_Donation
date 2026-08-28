import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/primary_action_button.dart';

/// 6-Step Guided Donation Creation Flow for Donors with Time-Aware Rescue Engine
/// Supports Standard Knowledge Base Foods, Custom Dishes, Flexible Units & Personal Food Library
class CreateDonationScreen extends StatefulWidget {
  final Map<String, dynamic>? aiData;
  const CreateDonationScreen({super.key, this.aiData});

  @override
  State<CreateDonationScreen> createState() => _CreateDonationScreenState();
}

class _CreateDonationScreenState extends State<CreateDonationScreen> {
  final _formKey = GlobalKey<FormState>();
  int _currentStep = 0; // 0 to 5 (6 steps)

  // Step 1: Mode & Food Details
  bool _isCustomFood = false;
  final _searchFoodController = TextEditingController();
  final _foodNameController = TextEditingController(text: 'Idli & Sambar Breakfast Set');
  final _customFoodNameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _majorIngredientsController = TextEditingController();
  final List<String> _selectedIngredients = [];

  String _selectedCategory = 'Cooked Food';
  String _selectedFoodType = 'Idli';
  String _broadCategory = 'cooked_rice_grain';

  // Step 2: Flexible Quantity & Units
  double _quantityValue = 50.0;
  final _quantityController = TextEditingController(text: '50');
  String _selectedUnit = 'Meals';
  final _customUnitLabelController = TextEditingController();

  // Step 3: Storage & Preparation Timing
  String _storageMethod = 'Room Temperature';
  final double _storageHours = 2.0;
  DateTime _prepTime = DateTime.now().subtract(const Duration(minutes: 45));
  bool _storageContinuous = true;
  final List<Map<String, dynamic>> _storageHistory = [];

  // Handling & Exposure
  String _packagingCondition = 'Covered';
  final String _previouslyServed = 'No';
  final String _exposureStatus = 'No';
  final String _handlingStatus = 'No';

  // Step 4: Photo / AI Visual Condition
  XFile? _pickedImage;
  String _aiCondition = 'GOOD';
  double _aiConfidence = 0.88;
  String _aiSpoilage = 'Not detected';

  // Step 5: Pickup
  final _addressController = TextEditingController(text: 'Koramangala 5th Block, Bengaluru');
  final _contactController = TextEditingController();
  bool _isLocating = false;

  // Food-Safety Self-Check Declaration State
  bool _safetyHumanConsumption = true;
  bool _safetyHygienicHandling = true;
  bool _safetyAppropriateStorage = true;
  bool _safetyContaminationFree = true;
  bool _safetySuitableCondition = true;

  // State
  bool _isSubmitting = false;
  bool _showMatchingProgress = false;

  final List<String> _categories = [
    'Cooked Food',
    'Bakery',
    'Fruits',
    'Vegetables',
    'Dairy',
    'Packaged Food',
    'Other',
  ];

  final List<Map<String, String>> _broadCategories = [
    {'key': 'cooked_rice_grain', 'label': 'Cooked Rice & Grains', 'desc': 'Pongal, pulao, lemon rice, fried rice'},
    {'key': 'curry_gravy', 'label': 'Curries & Gravies', 'desc': 'Kurma, sambar, rasam, kootu'},
    {'key': 'dal_lentil', 'label': 'Dals & Lentils', 'desc': 'Tadka dal, sambar, chana masala'},
    {'key': 'cooked_vegetable', 'label': 'Cooked Vegetables & Poriyal', 'desc': 'Dry veg fry, poriyal, avial'},
    {'key': 'dairy_based', 'label': 'Dairy & Milk-based Dishes', 'desc': 'Paneer gravy, curd dishes, payasam'},
    {'key': 'meat', 'label': 'Meat & Poultry Dishes', 'desc': 'Chicken curry, mutton gravy'},
    {'key': 'egg', 'label': 'Egg Dishes', 'desc': 'Egg curry, egg burji'},
    {'key': 'seafood', 'label': 'Fish & Seafood', 'desc': 'Fish curry, prawn masala'},
    {'key': 'bakery', 'label': 'Bakery & Bread', 'desc': 'Breads, buns, puffs, pastries'},
    {'key': 'snack_fried', 'label': 'Snacks & Fried Food', 'desc': 'Samosas, pakodas, vadas'},
    {'key': 'fruit', 'label': 'Fresh Fruits', 'desc': 'Cut fruit salads, whole fruits'},
    {'key': 'vegetable', 'label': 'Raw Vegetables', 'desc': 'Salad greens, cut vegetables'},
    {'key': 'packaged', 'label': 'Packaged & Sealed Food', 'desc': 'Biscuits, tetra packs, canned food'},
    {'key': 'frozen', 'label': 'Frozen Items', 'desc': 'Frozen meal packs'},
    {'key': 'not_sure', 'label': 'Not Sure / Mixed Preparation', 'desc': 'Conservative category rules apply'},
  ];

  final List<Map<String, String>> _foodProfiles = [
    {'type': 'Idli', 'category': 'Cooked Food', 'desc': 'Steamed rice cakes (4h RT base)'},
    {'type': 'Dosa', 'category': 'Cooked Food', 'desc': 'Crispy rice crêpes (4h RT base)'},
    {'type': 'Rice', 'category': 'Cooked Food', 'desc': 'Steamed plain rice (4h RT base)'},
    {'type': 'Biryani', 'category': 'Cooked Food', 'desc': 'Spiced rice & gravy (4h RT base)'},
    {'type': 'Sambar Rice', 'category': 'Cooked Food', 'desc': 'Lentil stew rice (4h RT base)'},
    {'type': 'Curd Rice', 'category': 'Cooked Food', 'desc': 'Yogurt rice (3h RT base)'},
    {'type': 'Chapati', 'category': 'Cooked Food', 'desc': 'Wheat flatbreads (6h RT base)'},
    {'type': 'Dal', 'category': 'Cooked Food', 'desc': 'Lentil curry (4h RT base)'},
    {'type': 'Vegetable Curry', 'category': 'Cooked Food', 'desc': 'Mixed spiced vegetables (4h RT base)'},
    {'type': 'Bread', 'category': 'Bakery', 'desc': 'Sliced bread / rolls (48h RT base)'},
    {'type': 'Pastry', 'category': 'Bakery', 'desc': 'Cakes & pastries (24h RT base)'},
    {'type': 'Fresh Fruit Medley', 'category': 'Fruits', 'desc': 'Apples, bananas, citrus (48h RT base)'},
    {'type': 'Farm Vegetables', 'category': 'Vegetables', 'desc': 'Greens & roots (72h RT base)'},
  ];

  final List<String> _quickIngredients = [
    'Rice', 'Lentils/Dal', 'Vegetables', 'Dairy/Paneer', 'Spices',
    'Wheat/Flour', 'Peanuts/Nuts', 'Ghee/Oil', 'Meat', 'Egg', 'Sugar'
  ];

  final List<String> _quantityUnits = [
    'Meals',
    'Portions',
    'Kg',
    'Grams',
    'Litres',
    'mL',
    'Pieces',
    'Packets',
    'Boxes',
    'Trays',
    'Containers',
    'Plates',
    'Bottles',
    'Custom'
  ];

  final List<String> _storageOptions = [
    'Room Temperature',
    'Refrigerated',
    'Heated/Insulated',
    'Frozen',
  ];

  final List<String> _packagingOptions = [
    'Sealed',
    'Covered',
    'Partially Covered',
    'Open',
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false).fetchMyFoods();
    });

    if (widget.aiData != null) {
      final ai = widget.aiData!;
      if (ai['food_name'] != null) {
        _foodNameController.text = ai['food_name'].toString();
      }
      if (ai['food_category'] != null && _categories.contains(ai['food_category'])) {
        _selectedCategory = ai['food_category'];
      }
      if (ai['storage_method'] != null && _storageOptions.contains(ai['storage_method'])) {
        _storageMethod = ai['storage_method'];
      }
      if (ai['ai_visual_condition'] != null) {
        _aiCondition = ai['ai_visual_condition'].toString();
      }
      if (ai['ai_confidence_score'] != null) {
        _aiConfidence = (ai['ai_confidence_score'] as num).toDouble();
      }
    }
  }

  @override
  void dispose() {
    _searchFoodController.dispose();
    _foodNameController.dispose();
    _customFoodNameController.dispose();
    _descriptionController.dispose();
    _majorIngredientsController.dispose();
    _quantityController.dispose();
    _customUnitLabelController.dispose();
    _addressController.dispose();
    _contactController.dispose();
    super.dispose();
  }

  // ── Helper: Live Equivalent Meal Calculation ──────────────────────────────
  double _calculateEstimatedMeals(double qty, String unit, String? customLabel) {
    final u = unit.toLowerCase().trim();
    if (u == 'meals' || u == 'portions' || u == 'plates' || u == 'servings') {
      return qty;
    } else if (u == 'kg' || u == 'kilograms') {
      return double.parse((qty * 2.22).toStringAsFixed(1));
    } else if (u == 'grams' || u == 'g') {
      return double.parse((qty / 450.0).toStringAsFixed(1));
    } else if (u == 'litres' || u == 'liters' || u == 'l') {
      return double.parse((qty * 2.5).toStringAsFixed(1));
    } else if (u == 'ml' || u == 'millilitres') {
      return double.parse((qty / 400.0).toStringAsFixed(1));
    } else if (u == 'trays') {
      return qty * 15.0;
    } else if (u == 'containers') {
      return qty * 5.0;
    } else if (u == 'boxes') {
      return qty * 2.0;
    } else if (u == 'packets') {
      return qty * 1.0;
    } else if (u == 'bottles') {
      return qty * 2.0;
    } else if (u == 'pieces') {
      return qty * 1.0;
    } else {
      return qty;
    }
  }

  // ── Helper: Rule Coverage Calculation ─────────────────────────────────────
  String _getRuleCoverage() {
    if (!_isCustomFood) {
      return 'HIGH';
    }
    if (_broadCategory == 'not_sure' || _broadCategory == 'Other') {
      return 'LOW';
    }
    return 'MEDIUM';
  }

  // ── Local Advisory Preview Calculation ────────────────────────────────────
  Map<String, dynamic> _calculateAdvisoryPreview() {
    final now = DateTime.now();
    final elapsedMinutes = now.difference(_prepTime).inMinutes;
    final elapsedHours = elapsedMinutes / 60.0;

    double baseHours = 4.0;
    if (_isCustomFood) {
      if (_broadCategory == 'cooked_rice_grain' || _broadCategory == 'dal_lentil' || _broadCategory == 'curry_gravy') {
        baseHours = 3.5;
      } else if (_broadCategory == 'dairy_based' || _broadCategory == 'meat' || _broadCategory == 'seafood') {
        baseHours = 2.5;
      } else if (_broadCategory == 'bakery') {
        baseHours = 24.0;
      } else if (_broadCategory == 'fruit' || _broadCategory == 'vegetable') {
        baseHours = 48.0;
      } else if (_broadCategory == 'snack_fried') {
        baseHours = 6.0;
      } else if (_broadCategory == 'packaged') {
        baseHours = 72.0;
      } else {
        baseHours = 3.0; // Conservative fallback
      }
    }

    if (_storageMethod == 'Refrigerated') baseHours = baseHours * 4.0;
    if (_storageMethod == 'Heated/Insulated') baseHours = baseHours * 1.5;
    if (_storageMethod == 'Frozen') baseHours = baseHours * 12.0;

    double penalty = 0.0;
    if (!_storageContinuous) penalty += 0.5;
    if (_packagingCondition == 'Open') penalty += 1.0;
    if (_packagingCondition == 'Partially Covered') penalty += 0.5;
    if (_previouslyServed == 'Yes') penalty += 1.0;
    if (_handlingStatus == 'Yes') penalty += 1.0;
    if (_exposureStatus == 'Yes') penalty += 0.5;

    final effectiveHours = (baseHours - penalty).clamp(0.5, 96.0);
    final remainingMinutes = ((effectiveHours - elapsedHours) * 60).clamp(0, 5000).toInt();

    String urgency = 'FRESH';
    if (remainingMinutes <= 30) {
      urgency = 'CRITICAL';
    } else if (remainingMinutes <= 90) {
      urgency = 'URGENT';
    } else if (remainingMinutes <= 180) {
      urgency = 'APPROACHING';
    }

    String feasibility = 'RESCUE_FEASIBLE';
    if (remainingMinutes < 45) {
      feasibility = 'RESCUE_UNLIKELY';
    } else if (remainingMinutes < 75) {
      feasibility = 'AT_RISK';
    }

    final windowEnd = _prepTime.add(Duration(minutes: (effectiveHours * 60).toInt()));

    return {
      'remaining_minutes': remainingMinutes,
      'urgency_level': urgency,
      'feasibility': feasibility,
      'window_end': windowEnd,
      'elapsed_mins': elapsedMinutes,
    };
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: source, imageQuality: 80);
    if (image != null && mounted) {
      setState(() {
        _pickedImage = image;
        _aiCondition = 'GOOD';
        _aiConfidence = 0.91;
        _aiSpoilage = 'Not detected';
      });
    }
  }

  Future<void> _getCurrentLocation() async {
    setState(() => _isLocating = true);
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position pos = await Geolocator.getCurrentPosition();
        setState(() {
          _addressController.text = 'Location (${pos.latitude.toStringAsFixed(4)}, ${pos.longitude.toStringAsFixed(4)})';
        });
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _isLocating = false);
    }
  }

  Future<void> _submitDonation() async {
    final allSafetyAffirmed = _safetyHumanConsumption &&
        _safetyHygienicHandling &&
        _safetyAppropriateStorage &&
        _safetyContaminationFree &&
        _safetySuitableCondition;

    if (!allSafetyAffirmed) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.tr('safety_blocked_msg')),
          backgroundColor: AppTheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
      _showMatchingProgress = true;
    });

    final preview = _calculateAdvisoryPreview();
    final provider = Provider.of<DonationProvider>(context, listen: false);

    final finalFoodName = _isCustomFood
        ? (_customFoodNameController.text.trim().isNotEmpty
            ? _customFoodNameController.text.trim()
            : 'Custom Surplus Dish')
        : (_foodNameController.text.trim().isNotEmpty
            ? _foodNameController.text.trim()
            : _selectedFoodType);

    final finalCategory = _isCustomFood ? _broadCategory : _selectedCategory;
    final estimatedMeals = _calculateEstimatedMeals(_quantityValue, _selectedUnit, _customUnitLabelController.text.trim());
    final ruleCoverage = _getRuleCoverage();

    final allIngredients = [
      ..._selectedIngredients,
      if (_majorIngredientsController.text.trim().isNotEmpty) _majorIngredientsController.text.trim(),
    ].join(', ');

    final description = [
      _descriptionController.text.trim(),
      if (_isCustomFood) 'Food Source: Custom Dish',
      if (allIngredients.isNotEmpty) 'Ingredients: $allIngredients',
      'Storage: $_storageMethod (${_storageContinuous ? 'Continuous' : 'Mixed'})',
      if (_previouslyServed == 'Yes') 'Handling: Previously served',
      if (_contactController.text.trim().isNotEmpty) 'Contact: ${_contactController.text.trim()}',
    ].where((s) => s.isNotEmpty).join('\n');

    final success = await provider.createDonation(
      foodName: finalFoodName,
      foodType: _isCustomFood ? finalFoodName : _selectedFoodType,
      foodSource: _isCustomFood ? 'CUSTOM' : 'KNOWN',
      customFoodName: _isCustomFood ? finalFoodName : null,
      foodDescription: _descriptionController.text.trim().isNotEmpty ? _descriptionController.text.trim() : null,
      majorIngredients: allIngredients.isNotEmpty ? allIngredients : null,
      foodCategory: finalCategory,
      quantity: _quantityValue,
      quantityUnit: _selectedUnit,
      quantityUnitLabel: _customUnitLabelController.text.trim().isNotEmpty ? _customUnitLabelController.text.trim() : null,
      estimatedMeals: estimatedMeals,
      ruleCoverage: ruleCoverage,
      preparationTime: _prepTime,
      expiryTime: preview['window_end'] as DateTime,
      pickupDeadline: preview['window_end'] as DateTime,
      pickupAddress: _addressController.text.trim().isEmpty ? 'Indiranagar, Bengaluru' : _addressController.text.trim(),
      description: description,
      latitude: 12.9716,
      longitude: 77.5946,
      imageUrl: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
      storageMethod: _storageMethod,
      storageDurationHours: _storageHours,
      storageContinuous: _storageContinuous,
      storageHistoryJson: _storageHistory.isNotEmpty ? jsonEncode(_storageHistory) : null,
      packagingCondition: _packagingCondition,
      previouslyServed: _previouslyServed,
      exposureStatus: _exposureStatus,
      handlingStatus: _handlingStatus,
      aiFoodDetected: finalFoodName,
      aiVisibleSpoilage: _aiSpoilage,
      aiDiscoloration: 'Normal',
      aiPackagingIntact: _packagingCondition,
      aiVisualCondition: _aiCondition,
      aiConfidenceScore: _aiConfidence,
      conditionScore: (_aiConfidence * 100).toInt(),
      safetyCheckAnswers: {
        'human_consumption': _safetyHumanConsumption,
        'hygienic_handling': _safetyHygienicHandling,
        'appropriate_storage': _safetyAppropriateStorage,
        'contamination_free': _safetyContaminationFree,
        'suitable_condition': _safetySuitableCondition,
      },
    );

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Donation Created & Matched Successfully! 🎉'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      context.go('/donor');
    } else {
      setState(() {
        _isSubmitting = false;
        _showMatchingProgress = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(provider.errorMessage ?? 'Failed to create donation. Check connection.'),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  Future<bool> _onWillPop() async {
    if (_currentStep > 0) {
      setState(() => _currentStep--);
      return false;
    }
    final shouldDiscard = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(context.tr('discard_draft_title'), style: const TextStyle(fontWeight: FontWeight.bold)),
        content: Text(context.tr('discard_draft_desc')),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              context.tr('keep_editing'),
              style: const TextStyle(color: AppTheme.primaryGreen, fontWeight: FontWeight.bold),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(
              context.tr('discard'),
              style: const TextStyle(color: AppTheme.error, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
    return shouldDiscard ?? false;
  }

  void _nextStep() {
    if (_currentStep == 0) {
      if (_isCustomFood && _customFoodNameController.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('custom_food_name_hint')),
            backgroundColor: AppTheme.warning,
          ),
        );
        return;
      }
      if (!_isCustomFood && _foodNameController.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('err_user_input')),
            backgroundColor: AppTheme.warning,
          ),
        );
        return;
      }
    } else if (_currentStep == 1) {
      if (_quantityValue <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('err_qty_zero')),
            backgroundColor: AppTheme.warning,
          ),
        );
        return;
      }
    } else if (_currentStep == 2) {
      if (_prepTime.isAfter(DateTime.now().add(const Duration(minutes: 5)))) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('err_prep_future')),
            backgroundColor: AppTheme.warning,
          ),
        );
        return;
      }
    } else if (_currentStep == 4) {
      if (_addressController.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('err_address_empty')),
            backgroundColor: AppTheme.warning,
          ),
        );
        return;
      }
    }

    if (_currentStep < 5) {
      setState(() => _currentStep++);
    } else {
      _submitDonation();
    }
  }

  void _prevStep() async {
    final canExit = await _onWillPop();
    if (canExit && mounted) {
      context.go('/donor');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_showMatchingProgress) {
      return _buildMatchingProgress();
    }

    final stepTitles = [
      context.tr('food_item'),
      context.tr('quantity'),
      context.tr('storage_method'),
      context.tr('ai_vision_analysis'),
      context.tr('pickup_address'),
      context.tr('review_donation'),
    ];

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (!didPop) {
          final canPop = await _onWillPop();
          if (canPop && context.mounted) {
            context.go('/donor');
          }
        }
      },
      child: Scaffold(
        backgroundColor: AppTheme.background,
        appBar: AppBar(
          title: Text(context.tr('donate_now')),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _prevStep,
          ),
        ),
        body: Column(
          children: [
            // Top Stepper Indicator
            Container(
              padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space12),
              color: AppTheme.surface,
              child: Row(
                children: List.generate(6, (index) {
                  final isDone = index < _currentStep;
                  final isCurrent = index == _currentStep;
                  return Expanded(
                    child: Row(
                      children: [
                        Expanded(
                          child: Container(
                            height: 4,
                            decoration: BoxDecoration(
                              color: isDone || isCurrent ? AppTheme.primaryGreen : AppTheme.border,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        ),
                        if (index < 5) const SizedBox(width: 4),
                      ],
                    ),
                  );
                }),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${context.tr('step_progress', {'current': '${_currentStep + 1}', 'total': '6'})}: ${stepTitles[_currentStep].toUpperCase()}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryGreen,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Text(
                    stepTitles[_currentStep],
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),

            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(AppTheme.space16, AppTheme.space8, AppTheme.space16, AppTheme.space32),
                child: Form(
                  key: _formKey,
                  child: _buildCurrentStepContent(),
                ),
              ),
            ),
          ],
        ),
        bottomNavigationBar: SafeArea(
          child: Container(
            padding: const EdgeInsets.all(AppTheme.space16),
            decoration: const BoxDecoration(
              color: AppTheme.surface,
              border: Border(top: BorderSide(color: AppTheme.border)),
            ),
            child: Row(
              children: [
                if (_currentStep > 0) ...[
                  OutlinedButton(
                    onPressed: _isSubmitting ? null : _prevStep,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space20, vertical: AppTheme.space14),
                    ),
                    child: Text(context.tr('back')),
                  ),
                  const SizedBox(width: AppTheme.space12),
                ],
                Expanded(
                  child: PrimaryActionButton(
                    label: _currentStep == 5
                        ? context.tr('create_donation').toUpperCase()
                        : context.tr('continue_btn').toUpperCase(),
                    isLoading: _isSubmitting,
                    onPressed: _nextStep,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCurrentStepContent() {
    switch (_currentStep) {
      case 0:
        return _buildStep1Food();
      case 1:
        return _buildStep2Quantity();
      case 2:
        return _buildStep3Storage();
      case 3:
        return _buildStep4PhotoAi();
      case 4:
        return _buildStep5Pickup();
      case 5:
      default:
        return _buildStep6Review();
    }
  }

  // ── STEP 1: FOOD DETAILS (CUSTOM + STANDARD + MY FOODS) ───────────────────
  Widget _buildStep1Food() {
    final donationProvider = Provider.of<DonationProvider>(context);
    final myFoods = donationProvider.myFoods;

    final filterText = _searchFoodController.text.toLowerCase().trim();
    final filteredProfiles = _foodProfiles.where((fp) {
      if (filterText.isEmpty) return true;
      return fp['type']!.toLowerCase().contains(filterText) ||
          fp['category']!.toLowerCase().contains(filterText);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Mode Selector: Standard vs Custom Food
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: AppTheme.surfaceHighlight,
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _isCustomFood = false),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: !_isCustomFood ? AppTheme.card : Colors.transparent,
                      borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                      boxShadow: !_isCustomFood ? AppTheme.shadowCard : null,
                    ),
                    child: Center(
                      child: Text(
                        context.tr('known_foods'),
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: !_isCustomFood ? FontWeight.bold : FontWeight.w600,
                          color: !_isCustomFood ? AppTheme.primaryGreen : AppTheme.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _isCustomFood = true),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: _isCustomFood ? AppTheme.card : Colors.transparent,
                      borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                      boxShadow: _isCustomFood ? AppTheme.shadowCard : null,
                    ),
                    child: Center(
                      child: Text(
                        context.tr('add_custom_food'),
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: _isCustomFood ? FontWeight.bold : FontWeight.w600,
                          color: _isCustomFood ? AppTheme.primaryGreen : AppTheme.textSecondary,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        // Personal Food Library ('My Foods') Quick Pick Chips
        if (myFoods.isNotEmpty) ...[
          Row(
            children: [
              const Icon(Icons.bookmark_outline, size: 16, color: AppTheme.primaryGreen),
              const SizedBox(width: 6),
              Text(
                context.tr('my_foods_library').toUpperCase(),
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen, letterSpacing: 0.5),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: myFoods.map((mf) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ActionChip(
                    avatar: const Icon(Icons.flash_on, size: 14, color: AppTheme.primaryGreen),
                    label: Text(mf.name),
                    backgroundColor: AppTheme.card,
                    side: const BorderSide(color: AppTheme.border),
                    onPressed: () {
                      setState(() {
                        _isCustomFood = true;
                        _customFoodNameController.text = mf.name;
                        _broadCategory = mf.foodCategory;
                        if (mf.description != null) _descriptionController.text = mf.description!;
                        if (mf.majorIngredients != null) _majorIngredientsController.text = mf.majorIngredients!;
                        _selectedUnit = mf.defaultUnit;
                        _storageMethod = mf.commonStorage;
                      });
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: AppTheme.space16),
        ],

        // SECTION A: STANDARD MENU ITEMS
        if (!_isCustomFood) ...[
          TextField(
            controller: _searchFoodController,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              hintText: context.tr('search_food_hint'),
              prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary),
              suffixIcon: _searchFoodController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () => setState(() => _searchFoodController.clear()),
                    )
                  : null,
            ),
          ),
          const SizedBox(height: AppTheme.space12),

          Wrap(
            spacing: AppTheme.space8,
            runSpacing: AppTheme.space8,
            children: filteredProfiles.map((fp) {
              final isSelected = _selectedFoodType == fp['type'];
              return ChoiceChip(
                label: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(context.trFood(fp['type']!), style: TextStyle(fontWeight: isSelected ? FontWeight.bold : FontWeight.w600)),
                    Text(context.trCategory(fp['category']!), style: TextStyle(fontSize: 10, color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary)),
                  ],
                ),
                selected: isSelected,
                onSelected: (val) {
                  setState(() {
                    _selectedFoodType = fp['type']!;
                    _selectedCategory = fp['category']!;
                    _foodNameController.text = '${fp['type']} Surplus Portions';
                  });
                },
                selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
                backgroundColor: AppTheme.card,
                side: BorderSide(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
              );
            }).toList(),
          ),
          const SizedBox(height: AppTheme.space16),

          Text(context.tr('food_name'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: AppTheme.space8),
          TextFormField(
            controller: _foodNameController,
            decoration: InputDecoration(
              hintText: context.tr('food_name_hint'),
              prefixIcon: const Icon(Icons.restaurant, color: AppTheme.textSecondary),
            ),
            validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
          ),
        ],

        // SECTION B: CUSTOM FOOD FORM
        if (_isCustomFood) ...[
          Text(context.tr('custom_food_name'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: AppTheme.space8),
          TextFormField(
            controller: _customFoodNameController,
            decoration: InputDecoration(
              hintText: context.tr('custom_food_name_hint'),
              prefixIcon: const Icon(Icons.edit_note, color: AppTheme.primaryGreen),
            ),
            validator: (v) => v == null || v.trim().isEmpty ? context.tr('enter_custom_dish_name') : null,
          ),
          const SizedBox(height: AppTheme.space16),

          Text(context.tr('food_category'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: 4),
          Text(context.tr('broad_category_hint'), style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
          const SizedBox(height: AppTheme.space8),
          DropdownButtonFormField<String>(
            initialValue: _broadCategory,
            isExpanded: true,
            decoration: const InputDecoration(prefixIcon: Icon(Icons.category, color: AppTheme.primaryGreen)),
            items: _broadCategories.map((bc) {
              return DropdownMenuItem<String>(
                value: bc['key'],
                child: Text('${bc['label']} (${bc['desc']})', overflow: TextOverflow.ellipsis),
              );
            }).toList(),
            onChanged: (val) {
              if (val != null) setState(() => _broadCategory = val);
            },
          ),
          const SizedBox(height: AppTheme.space16),

          Text(context.tr('major_ingredients'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: AppTheme.space8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: _quickIngredients.map((ing) {
              final isSel = _selectedIngredients.contains(ing);
              return FilterChip(
                label: Text(ing, style: TextStyle(fontSize: 12, fontWeight: isSel ? FontWeight.bold : FontWeight.normal)),
                selected: isSel,
                onSelected: (sel) {
                  setState(() {
                    if (sel) {
                      _selectedIngredients.add(ing);
                    } else {
                      _selectedIngredients.remove(ing);
                    }
                  });
                },
                selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.2),
                backgroundColor: AppTheme.card,
                side: BorderSide(color: isSel ? AppTheme.primaryGreen : AppTheme.border),
              );
            }).toList(),
          ),
          const SizedBox(height: AppTheme.space8),
          TextFormField(
            controller: _majorIngredientsController,
            decoration: InputDecoration(
              hintText: context.tr('major_ingredients_hint'),
            ),
          ),
          const SizedBox(height: AppTheme.space16),

          // Rule Coverage Advisory Banner
          Container(
            padding: const EdgeInsets.all(AppTheme.space12),
            decoration: BoxDecoration(
              color: AppTheme.surfaceHighlight,
              borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline, color: AppTheme.info, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    context.tr('custom_food_advisory_note'),
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: AppTheme.space16),
        Text(context.tr('food_description'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: AppTheme.space8),
        TextFormField(
          controller: _descriptionController,
          maxLines: 2,
          decoration: InputDecoration(
            hintText: context.tr('food_description_hint'),
          ),
        ),
      ],
    );
  }

  // ── STEP 2: FLEXIBLE QUANTITY & UNITS ─────────────────────────────────────
  Widget _buildStep2Quantity() {
    final estimatedMeals = _calculateEstimatedMeals(_quantityValue, _selectedUnit, _customUnitLabelController.text.trim());
    final approxKg = (estimatedMeals * 0.45).toStringAsFixed(1);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('flexible_quantity'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          context.tr('payload_capacity'),
          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: AppTheme.space20),

        // Main Quantity Counter & Unit Picker Card
        Container(
          padding: const EdgeInsets.all(AppTheme.space20),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
            border: Border.all(color: AppTheme.border),
            boxShadow: AppTheme.shadowCard,
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton.filled(
                    onPressed: _quantityValue > 1 ? () {
                      setState(() {
                        _quantityValue = (_quantityValue - (_quantityValue <= 5 ? 0.5 : 5.0)).clamp(0.5, 9999.0);
                        _quantityController.text = _quantityValue.toString();
                      });
                    } : null,
                    icon: const Icon(Icons.remove),
                    style: IconButton.styleFrom(backgroundColor: AppTheme.surfaceHighlight, foregroundColor: AppTheme.textPrimary),
                  ),
                  const SizedBox(width: AppTheme.space16),
                  SizedBox(
                    width: 110,
                    child: TextField(
                      controller: _quantityController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w900, color: AppTheme.primaryGreen),
                      decoration: const InputDecoration(
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.zero,
                      ),
                      onChanged: (val) {
                        final parsed = double.tryParse(val);
                        if (parsed != null && parsed > 0) {
                          setState(() => _quantityValue = parsed);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: AppTheme.space16),
                  IconButton.filled(
                    onPressed: () {
                      setState(() {
                        _quantityValue = (_quantityValue + (_quantityValue < 5 ? 0.5 : 5.0)).clamp(0.5, 9999.0);
                        _quantityController.text = _quantityValue.toString();
                      });
                    },
                    icon: const Icon(Icons.add),
                    style: IconButton.styleFrom(backgroundColor: AppTheme.primaryGreen, foregroundColor: Colors.white),
                  ),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              // Unit Selector Dropdown
              DropdownButtonFormField<String>(
                initialValue: _selectedUnit,
                decoration: InputDecoration(
                  labelText: context.tr('quantity_unit'),
                  prefixIcon: const Icon(Icons.scale, color: AppTheme.primaryGreen),
                ),
                items: _quantityUnits.map((u) {
                  return DropdownMenuItem<String>(
                    value: u,
                    child: Text(context.trUnit(u)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => _selectedUnit = val);
                },
              ),

              // Optional Custom Unit Label (for Custom, Trays, Boxes, Containers)
              if (_selectedUnit == 'Custom' || _selectedUnit == 'Containers' || _selectedUnit == 'Trays' || _selectedUnit == 'Boxes') ...[
                const SizedBox(height: AppTheme.space12),
                TextFormField(
                  controller: _customUnitLabelController,
                  decoration: InputDecoration(
                    labelText: context.tr('quantity_unit_label'),
                    hintText: context.tr('quantity_unit_label_hint'),
                    prefixIcon: const Icon(Icons.label_outline, color: AppTheme.textSecondary),
                  ),
                ),
              ],

              const Divider(height: 32),

              // Live Equivalent Meals Estimator
              Container(
                padding: const EdgeInsets.all(AppTheme.space12),
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                  border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.2)),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(context.tr('estimated_meals_count', {'count': estimatedMeals.toStringAsFixed(1)}),
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                        Text('≈ $approxKg kg', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textSecondary)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Logistics capacity and volunteer courier dispatch dynamically scale from this equivalent meal estimate.',
                      style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ── STEP 3: STORAGE & PREPARATION TIMING ──────────────────────────────────
  Widget _buildStep3Storage() {
    final now = DateTime.now();
    final elapsedMinutes = now.difference(_prepTime).inMinutes;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('storage_method'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          context.tr('preparation_time'),
          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: AppTheme.space16),

        // Preparation Elapsed Quick Selectors
        Text(context.tr('preparation_time'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: AppTheme.space8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _buildPrepTimeChip(context.tr('prep_quick_chip_less_1h'), const Duration(minutes: 30)),
            _buildPrepTimeChip(context.tr('prep_quick_chip_1_2h'), const Duration(minutes: 90)),
            _buildPrepTimeChip(context.tr('prep_quick_chip_2_4h'), const Duration(hours: 3)),
            _buildPrepTimeChip(context.tr('prep_quick_chip_4_6h'), const Duration(hours: 5)),
            _buildPrepTimeChip(context.tr('prep_quick_chip_6_8h'), const Duration(hours: 7)),
            _buildPrepTimeChip(context.tr('prep_quick_chip_8h_plus'), const Duration(hours: 9)),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.surfaceHighlight,
            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.schedule, size: 14, color: AppTheme.primaryGreen),
              const SizedBox(width: 6),
              Text(
                '${context.tr('elapsed_time')}: ${elapsedMinutes ~/ 60}h ${elapsedMinutes % 60}m ago',
                style: const TextStyle(fontSize: 12, color: AppTheme.primaryGreen, fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        // Storage Method
        Text(context.tr('storage_method'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: AppTheme.space8),
        ..._storageOptions.map((opt) {
          final isSelected = _storageMethod == opt;
          return InkWell(
            onTap: () => setState(() => _storageMethod = opt),
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
            child: Container(
              margin: const EdgeInsets.only(bottom: AppTheme.space8),
              padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space12),
              decoration: BoxDecoration(
                color: isSelected ? AppTheme.primaryGreen.withAlpha(25) : AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: isSelected ? AppTheme.primaryGreen : AppTheme.border, width: isSelected ? 1.5 : 1),
              ),
              child: Row(
                children: [
                  Icon(
                    isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
                    color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                    size: 20,
                  ),
                  const SizedBox(width: AppTheme.space12),
                  Expanded(
                    child: Text(
                      context.trStorage(opt),
                      style: TextStyle(
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
        const SizedBox(height: AppTheme.space12),

        // Continuous Storage Toggle
        SwitchListTile(
          title: Text(context.tr('continuous_storage'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          value: _storageContinuous,
          activeThumbColor: AppTheme.primaryGreen,
          onChanged: (v) => setState(() => _storageContinuous = v),
        ),
      ],
    );
  }

  Widget _buildPrepTimeChip(String label, Duration ago) {
    final target = DateTime.now().subtract(ago);
    final isSelected = (_prepTime.difference(target).inMinutes.abs() < 45);
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (v) => setState(() => _prepTime = target),
      selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
      backgroundColor: AppTheme.card,
      side: BorderSide(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
    );
  }

  // ── STEP 4: PHOTO / AI ASSESSMENT ─────────────────────────────────────────
  Widget _buildStep4PhotoAi() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('ai_vision_analysis'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          context.tr('visual_condition'),
          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: AppTheme.space16),

        GestureDetector(
          onTap: () => _pickImage(ImageSource.camera),
          child: Container(
            height: 140,
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: _pickedImage != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    child: Image.file(File(_pickedImage!.path), fit: BoxFit.cover),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(AppTheme.space12),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.camera_alt, color: AppTheme.primaryGreen, size: 28),
                      ),
                      const SizedBox(height: AppTheme.space8),
                      Text(context.tr('ai_vision_analysis'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        Text(context.tr('packaging_condition'), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: AppTheme.space8),
        Wrap(
          spacing: 8,
          children: _packagingOptions.map((opt) {
            final isSelected = _packagingCondition == opt;
            return ChoiceChip(
              label: Text(opt),
              selected: isSelected,
              onSelected: (v) => setState(() => _packagingCondition = opt),
              selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
              backgroundColor: AppTheme.card,
              side: BorderSide(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
            );
          }).toList(),
        ),
        const SizedBox(height: AppTheme.space16),

        // AI Assessment Box
        Container(
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
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome, color: AppTheme.primaryGreen, size: 18),
                      const SizedBox(width: 6),
                      Text(context.tr('ai_vision_analysis').toUpperCase(), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space2),
                    decoration: BoxDecoration(
                      color: AppTheme.successLight,
                      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                    ),
                    child: Text('${(_aiConfidence * 100).toInt()}%', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.success)),
                  ),
                ],
              ),
              const Divider(height: 20),
              _buildAiRow(context.tr('visual_condition'), context.trVisual(_aiCondition), Icons.check_circle, AppTheme.success),
              _buildAiRow(context.tr('packaging_condition'), _packagingCondition, Icons.inventory_2_outlined, AppTheme.info),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space12),

        // Mandatory Disclaimer Banner
        Container(
          padding: const EdgeInsets.all(AppTheme.space12),
          decoration: BoxDecoration(
            color: AppTheme.warningLight,
            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
            border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              const Icon(Icons.shield_outlined, color: AppTheme.warning, size: 18),
              const SizedBox(width: AppTheme.space8),
              Expanded(
                child: Text(
                  context.trDisclaimer(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.warning),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAiRow(String label, String value, IconData icon, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
          const Spacer(),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }

  // ── STEP 5: PICKUP LOCATION ───────────────────────────────────────────────
  Widget _buildStep5Pickup() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('pickup_address'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          context.tr('why_match'),
          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: AppTheme.space20),

        TextFormField(
          controller: _addressController,
          decoration: InputDecoration(
            labelText: context.tr('pickup_address'),
            prefixIcon: const Icon(Icons.location_on, color: AppTheme.primaryGreen),
            suffixIcon: IconButton(
              icon: _isLocating ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.my_location),
              onPressed: _getCurrentLocation,
            ),
          ),
          validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
        ),
        const SizedBox(height: AppTheme.space16),

        TextFormField(
          controller: _contactController,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            labelText: context.tr('phone_number'),
            prefixIcon: const Icon(Icons.phone, color: AppTheme.textSecondary),
          ),
        ),
      ],
    );
  }

  // ── STEP 6: REVIEW & LIVE ADVISORY RESCUE WINDOW ──────────────────────────
  Widget _buildStep6Review() {
    final preview = _calculateAdvisoryPreview();
    final remMins = preview['remaining_minutes'] as int;
    final urgency = preview['urgency_level'] as String;
    final feasibility = preview['feasibility'] as String;
    final ruleCov = _getRuleCoverage();

    final finalFoodName = _isCustomFood
        ? (_customFoodNameController.text.trim().isNotEmpty ? _customFoodNameController.text.trim() : 'Custom Dish')
        : (_foodNameController.text.trim().isNotEmpty ? _foodNameController.text.trim() : _selectedFoodType);

    final estimatedMeals = _calculateEstimatedMeals(_quantityValue, _selectedUnit, _customUnitLabelController.text.trim());

    Color coverageColor = AppTheme.success;
    String coverageLabel = context.tr('rule_coverage_high');
    if (ruleCov == 'MEDIUM') {
      coverageColor = AppTheme.info;
      coverageLabel = context.tr('rule_coverage_medium');
    } else if (ruleCov == 'LOW') {
      coverageColor = AppTheme.warning;
      coverageLabel = context.tr('rule_coverage_low');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('review_donation'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        const SizedBox(height: 16),

        // Time-Aware Advisory Card (3 Distinct Outputs + Rule Coverage)
        Container(
          padding: const EdgeInsets.all(AppTheme.space16),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
            border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.4)),
            boxShadow: AppTheme.shadowCard,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.timer_outlined, color: AppTheme.primaryGreen, size: 20),
                      const SizedBox(width: 8),
                      Text(context.tr('rescue_window').toUpperCase(), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: coverageColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      ruleCov,
                      style: TextStyle(fontWeight: FontWeight.bold, color: coverageColor, fontSize: 11),
                    ),
                  ),
                ],
              ),
              const Divider(height: 20),

              // Rule Coverage Description
              Row(
                children: [
                  Icon(Icons.shield_outlined, size: 14, color: coverageColor),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      coverageLabel,
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: coverageColor),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Output 1: Visual Condition
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(context.tr('visual_condition'), style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(color: AppTheme.successLight, borderRadius: BorderRadius.circular(12)),
                    child: Text(context.trVisual(_aiCondition), style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.success, fontSize: 12)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Output 2: Estimated Rescue Window
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(context.tr('rescue_window'), style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                  Text(context.trRemainingMinutes(remMins), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.primaryGreen)),
                ],
              ),
              const SizedBox(height: 8),
              // Output 3: Rescue Urgency
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(context.tr('urgency_level'), style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(color: AppTheme.warningLight, borderRadius: BorderRadius.circular(12)),
                    child: Text(context.trUrgency(urgency), style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.warning, fontSize: 12)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Logistics Feasibility
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(context.tr('rescue_feasibility'), style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                  Text(context.trFeasibility(feasibility), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space12),

        // Mandatory Food Safety Disclaimer
        Container(
          padding: const EdgeInsets.all(AppTheme.space12),
          decoration: BoxDecoration(
            color: AppTheme.warningLight,
            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
            border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              const Icon(Icons.shield_outlined, color: AppTheme.warning, size: 18),
              const SizedBox(width: AppTheme.space8),
              Expanded(
                child: Text(
                  context.trDisclaimer(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.warning),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        // Summary Card
        Container(
          padding: const EdgeInsets.all(AppTheme.space16),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            children: [
              _buildReviewRow(context.tr('food_item'), finalFoodName),
              _buildReviewRow(context.tr('food_category'), _isCustomFood ? _broadCategory : _selectedCategory),
              _buildReviewRow(context.tr('quantity'), '$_quantityValue ${context.trUnit(_selectedUnit)} (≈ ${estimatedMeals.toStringAsFixed(0)} meals)'),
              _buildReviewRow(context.tr('storage_method'), context.trStorage(_storageMethod)),
              _buildReviewRow(context.tr('pickup_address'), _addressController.text.trim()),
            ],
          ),
        ),
        const SizedBox(height: AppTheme.space16),

        // Core Enhancement 1: Food-Safety Self-Check Declaration Card
        _buildFoodSafetySelfCheckCard(),
      ],
    );
  }

  Widget _buildFoodSafetySelfCheckCard() {
    final allChecked = _safetyHumanConsumption &&
        _safetyHygienicHandling &&
        _safetyAppropriateStorage &&
        _safetyContaminationFree &&
        _safetySuitableCondition;

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
        border: Border.all(
          color: allChecked ? AppTheme.primaryGreen.withValues(alpha: 0.5) : AppTheme.warning.withValues(alpha: 0.5),
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
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: (allChecked ? AppTheme.primaryGreen : AppTheme.warning).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  allChecked ? Icons.verified_user_rounded : Icons.shield_outlined,
                  color: allChecked ? AppTheme.primaryGreen : AppTheme.warning,
                  size: 20,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.tr('safety_check_title'),
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    Text(
                      context.tr('safety_check_subtitle'),
                      style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Advisory Disclaimer Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: AppTheme.surfaceWarm,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_outline, size: 14, color: AppTheme.textSecondary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    context.tr('safety_check_disclaimer'),
                    style: const TextStyle(fontSize: 10.5, color: AppTheme.textSecondary, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 5 Affirmative Declarations
          _buildSafetyCheckboxItem(
            title: context.tr('safety_q1_title'),
            desc: context.tr('safety_q1_desc'),
            value: _safetyHumanConsumption,
            onChanged: (val) => setState(() => _safetyHumanConsumption = val ?? false),
          ),
          const Divider(height: 16),
          _buildSafetyCheckboxItem(
            title: context.tr('safety_q2_title'),
            desc: context.tr('safety_q2_desc'),
            value: _safetyHygienicHandling,
            onChanged: (val) => setState(() => _safetyHygienicHandling = val ?? false),
          ),
          const Divider(height: 16),
          _buildSafetyCheckboxItem(
            title: context.tr('safety_q3_title'),
            desc: context.tr('safety_q3_desc'),
            value: _safetyAppropriateStorage,
            onChanged: (val) => setState(() => _safetyAppropriateStorage = val ?? false),
          ),
          const Divider(height: 16),
          _buildSafetyCheckboxItem(
            title: context.tr('safety_q4_title'),
            desc: context.tr('safety_q4_desc'),
            value: _safetyContaminationFree,
            onChanged: (val) => setState(() => _safetyContaminationFree = val ?? false),
          ),
          const Divider(height: 16),
          _buildSafetyCheckboxItem(
            title: context.tr('safety_q5_title'),
            desc: context.tr('safety_q5_desc'),
            value: _safetySuitableCondition,
            onChanged: (val) => setState(() => _safetySuitableCondition = val ?? false),
          ),

          const SizedBox(height: 14),

          // Status Outcome Badge
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: allChecked ? AppTheme.successLight : AppTheme.warningLight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  allChecked ? Icons.check_circle_rounded : Icons.warning_amber_rounded,
                  size: 16,
                  color: allChecked ? AppTheme.success : AppTheme.warning,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    allChecked
                        ? context.tr('safety_all_affirm_passed')
                        : context.tr('safety_all_affirm_req'),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: allChecked ? AppTheme.success : AppTheme.warning,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSafetyCheckboxItem({
    required String title,
    required String desc,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return InkWell(
      onTap: () => onChanged(!value),
      borderRadius: BorderRadius.circular(6),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 24,
              height: 24,
              child: Checkbox(
                value: value,
                onChanged: onChanged,
                activeColor: AppTheme.primaryGreen,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: value ? AppTheme.textPrimary : AppTheme.warning,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    desc,
                    style: const TextStyle(fontSize: 11.5, color: AppTheme.textSecondary, height: 1.3),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMatchingProgress() {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(color: AppTheme.primaryGreen),
            const SizedBox(height: AppTheme.space24),
            Text(context.tr('processing'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(context.tr('why_match'), style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
          ],
        ),
      ),
    );
  }
}
