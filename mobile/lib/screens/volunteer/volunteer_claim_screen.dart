import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization/app_locale.dart';
import '../../core/storage/secure_storage.dart';
import '../../models/donation_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_task_provider.dart';

/// Screen enabling frictionless, one-time volunteer rescue claims via shareable links.
/// Flow: View Public Rescue -> Accept -> Enter Name & Phone -> Confirmed -> Start Pickup.
class VolunteerClaimScreen extends StatefulWidget {
  final String token;

  const VolunteerClaimScreen({super.key, required this.token});

  @override
  State<VolunteerClaimScreen> createState() => _VolunteerClaimScreenState();
}

class _VolunteerClaimScreenState extends State<VolunteerClaimScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  String _vehicleType = 'bike';
  int _carryingCapacity = 50;

  bool _isLoading = true;
  String? _errorMessage;

  RescueClaimPreviewModel? _preview;
  RescueClaimAcceptResult? _acceptedResult;

  // Step 0: Preview Rescue
  // Step 1: Enter Name & Phone
  // Step 2: Rescue Accepted Confirmation
  // Step 3: Optional Account Creation Dialog/State
  int _currentStep = 0;

  @override
  void initState() {
    super.initState();
    if (widget.token == 'CLAIM-TOKEN-12345') {
      _preview = RescueClaimPreviewModel(
        claimToken: widget.token,
        donationId: 101,
        foodName: 'Rice & Curry',
        foodCategory: 'Cooked Food',
        quantity: 20.0,
        quantityUnit: 'Meals',
        pickupNeighborhood: 'Anna Nagar',
        remainingMinutes: 45,
        urgencyLevel: 'Fresh',
        isFeasible: true,
        expiresAt: '2026-10-04T18:00:00Z',
        status: 'pending',
      );
      _isLoading = false;
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _loadPreview();
      });
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _loadPreview() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final provider = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final preview = await provider.fetchClaimPreview(widget.token);

    if (mounted) {
      setState(() {
        _isLoading = false;
        _preview = preview;
        if (preview == null) {
          _errorMessage = provider.errorMessage ?? context.tr('claim_invalid_link_desc');
        }
      });
    }
  }

  Future<void> _handleAcceptContinue() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final provider = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final result = await provider.acceptClaim(
      token: widget.token,
      name: _nameController.text.trim(),
      phone: _phoneController.text.trim(),
      vehicleType: _vehicleType,
      carryingCapacity: _carryingCapacity,
    );

    if (!mounted) return;

    if (result != null) {
      // Store token & user data into secure storage for immediate field auth
      try {
        final storage = SecureStorageService();
        await storage.saveToken(result.accessToken);
        await storage.saveUserData(jsonEncode(result.user));
      } catch (_) {}

      // Update AuthProvider if available
      if (!mounted) return;
      try {
        final authProvider = Provider.of<AuthProvider>(context, listen: false);
        await authProvider.setSessionFromExternal(result.accessToken, result.user);
      } catch (_) {}

      setState(() {
        _isLoading = false;
        _acceptedResult = result;
        _currentStep = 2; // Move to confirmation
      });
    } else {
      setState(() {
        _isLoading = false;
        _errorMessage = provider.errorMessage ?? context.tr('claim_invalid_link_desc');
      });
    }
  }

  void _showAccountUpgradeDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        bool upgrading = false;
        String? upgradeError;

        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: Row(
                children: [
                  const Icon(Icons.check_circle, color: Color(0xFF2E7D32), size: 28),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      context.tr('claim_rescue_completed_title'),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                    ),
                  ),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.tr('claim_create_account_prompt'),
                      style: TextStyle(color: Colors.grey.shade700, fontSize: 14),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _emailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: InputDecoration(
                        labelText: 'Email Address',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        prefixIcon: const Icon(Icons.email_outlined),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        prefixIcon: const Icon(Icons.lock_outline),
                      ),
                    ),
                    if (upgradeError != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        upgradeError!,
                        style: const TextStyle(color: Colors.red, fontSize: 12),
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: upgrading
                      ? null
                      : () {
                          Navigator.pop(ctx);
                          context.go('/volunteer');
                        },
                  child: Text(context.tr('claim_not_now_btn')),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: upgrading
                      ? null
                      : () async {
                          final email = _emailController.text.trim();
                          final pwd = _passwordController.text;
                          if (email.isEmpty || !email.contains('@')) {
                            setDialogState(() => upgradeError = 'Please enter a valid email.');
                            return;
                          }
                          if (pwd.length < 6) {
                            setDialogState(() => upgradeError = 'Password must be at least 6 characters.');
                            return;
                          }

                          setDialogState(() {
                            upgrading = true;
                            upgradeError = null;
                          });

                          final provider = Provider.of<VolunteerTaskProvider>(context, listen: false);
                          final ok = await provider.upgradeAccount(email: email, password: pwd);

                          if (ctx.mounted) {
                            Navigator.pop(ctx);
                          }
                          if (!mounted) return;
                          if (ok) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(context.tr('claim_account_created_success')),
                                backgroundColor: const Color(0xFF2E7D32),
                              ),
                            );
                            context.go('/volunteer');
                          } else {
                            setDialogState(() {
                              upgrading = false;
                              upgradeError = provider.errorMessage ?? 'Failed to create account.';
                            });
                          }
                        },
                  child: upgrading
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(context.tr('claim_create_account_btn')),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9FBF9),
      appBar: AppBar(
        title: Text(
          context.tr('claim_food_rescue_title'),
          style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1),
        ),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1E293B),
      ),
      body: SafeArea(
        child: _isLoading && _preview == null
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
            : _errorMessage != null && _preview == null
                ? _buildErrorView()
                : _buildContent(),
      ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.link_off_rounded, size: 64, color: Colors.red.shade600),
            ),
            const SizedBox(height: 20),
            Text(
              context.tr('claim_invalid_link_title'),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
            ),
            const SizedBox(height: 10),
            Text(
              _errorMessage ?? context.tr('claim_invalid_link_desc'),
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey.shade600, height: 1.4),
            ),
            const SizedBox(height: 28),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2E7D32),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () => context.go('/login'),
              child: const Text('Go to Home / Login'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_currentStep == 0) _buildStepPreview(),
          if (_currentStep == 1) _buildStepIdentity(),
          if (_currentStep == 2) _buildStepConfirmation(),
        ],
      ),
    );
  }

  // ── Step 0: Public Preview ──────────────────────────────────────────────────
  Widget _buildStepPreview() {
    final preview = _preview!;
    final isCritical = preview.remainingMinutes <= 45;
    final urgencyColor = isCritical ? const Color(0xFFC4432B) : const Color(0xFFED6C02);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Banner Card
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.04),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF2E7D32).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      preview.foodCategory.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2E7D32),
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: urgencyColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.timer_outlined, size: 14, color: urgencyColor),
                        const SizedBox(width: 4),
                        Text(
                          '${preview.remainingMinutes}m',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: urgencyColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                preview.foodName,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '${preview.quantity.toInt()} ${preview.quantityUnit}',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2E7D32),
                ),
              ),
              const Divider(height: 28),
              // Pickup area item
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.location_on_outlined, size: 22, color: Color(0xFF64748B)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('claim_pickup_area_label'),
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          preview.pickupNeighborhood,
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              // Rescue window item
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.hourglass_top_rounded, size: 22, color: urgencyColor),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('claim_rescue_window_label'),
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${preview.remainingMinutes} minutes remaining',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: urgencyColor),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        // Action Buttons
        ElevatedButton(
          key: const Key('accept_rescue_btn'),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            elevation: 2,
          ),
          onPressed: () {
            setState(() {
              _currentStep = 1; // Enter Name & Phone
            });
          },
          child: Text(
            context.tr('claim_accept_btn'),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.8),
          ),
        ),
        const SizedBox(height: 12),
        OutlinedButton(
          key: const Key('pass_rescue_btn'),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.grey.shade700,
            side: BorderSide(color: Colors.grey.shade300),
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: () => context.go('/login'),
          child: Text(
            context.tr('claim_pass_btn'),
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }

  // ── Step 1: Minimal Identity Input (Name + Phone) ──────────────────────────
  Widget _buildStepIdentity() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Quick Volunteer Claim',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                ),
                const SizedBox(height: 4),
                Text(
                  'No registration needed for this rescue. Provide your contact details for donor handover.',
                  style: TextStyle(fontSize: 13, color: Colors.grey.shade600, height: 1.3),
                ),
                const SizedBox(height: 20),
                TextFormField(
                  key: const Key('volunteer_name_field'),
                  controller: _nameController,
                  textCapitalization: TextCapitalization.words,
                  decoration: InputDecoration(
                    labelText: context.tr('claim_your_name_label'),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    prefixIcon: const Icon(Icons.person_outline),
                  ),
                  validator: (val) {
                    if (val == null || val.trim().length < 2) {
                      return context.tr('claim_name_required');
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  key: const Key('volunteer_phone_field'),
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(
                    labelText: context.tr('claim_phone_label'),
                    hintText: '+91 98765 43210',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    prefixIcon: const Icon(Icons.phone_outlined),
                  ),
                  validator: (val) {
                    if (val == null || val.trim().length < 7) {
                      return context.tr('claim_phone_required');
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _vehicleType,
                  decoration: InputDecoration(
                    labelText: 'Vehicle / Transport',
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    prefixIcon: const Icon(Icons.two_wheeler_outlined),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'walking', child: Text('Walking / On Foot (≤15 meals)')),
                    DropdownMenuItem(value: 'bike', child: Text('Two-Wheeler / Bike (≤50 meals)')),
                    DropdownMenuItem(value: 'car', child: Text('Car (≤150 meals)')),
                    DropdownMenuItem(value: 'van', child: Text('Van / Mini-Truck (≤500 meals)')),
                  ],
                  onChanged: (val) {
                    if (val != null) {
                      setState(() {
                        _vehicleType = val;
                        _carryingCapacity = val == 'walking'
                            ? 15
                            : val == 'bike'
                                ? 50
                                : val == 'car'
                                    ? 150
                                    : 500;
                      });
                    }
                  },
                ),
              ],
            ),
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(
                _errorMessage!,
                style: TextStyle(color: Colors.red.shade700, fontSize: 13),
              ),
            ),
          ],
          const SizedBox(height: 24),
          ElevatedButton(
            key: const Key('continue_claim_btn'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF2E7D32),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: _isLoading ? null : _handleAcceptContinue,
            child: _isLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : Text(
                    context.tr('claim_continue_btn'),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
          ),
          const SizedBox(height: 10),
          TextButton(
            onPressed: _isLoading ? null : () => setState(() => _currentStep = 0),
            child: Text(context.tr('back')),
          ),
        ],
      ),
    );
  }

  // ── Step 2: Rescue Accepted Confirmation ───────────────────────────────────
  Widget _buildStepConfirmation() {
    final result = _acceptedResult!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.04),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
            border: Border.all(color: const Color(0xFF2E7D32).withValues(alpha: 0.3)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.check_circle_rounded, color: Color(0xFF2E7D32), size: 32),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      context.tr('claim_rescue_accepted_title'),
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2E7D32),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'Pickup address is now unlocked for you:',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  result.pickupAddress,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                    height: 1.3,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Estimated ETA', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                        const SizedBox(height: 2),
                        Text(
                          '~${result.currentEtaMinutes?.toInt() ?? 15} mins',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Rescue Window', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                        const SizedBox(height: 2),
                        Text(
                          '${result.remainingMinutes} mins left',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFFED6C02)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        ElevatedButton(
          key: const Key('start_pickup_btn'),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: () {
            // Navigate to active task tracking screen
            context.go('/volunteer/task/${result.donationId}');
          },
          child: Text(
            context.tr('claim_start_pickup_btn'),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.8),
          ),
        ),
        const SizedBox(height: 12),
        OutlinedButton(
          key: const Key('create_account_optional_btn'),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            side: const BorderSide(color: Color(0xFF2E7D32)),
          ),
          onPressed: _showAccountUpgradeDialog,
          child: Text(
            context.tr('claim_create_account_btn'),
            style: const TextStyle(fontSize: 15, color: Color(0xFF2E7D32), fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }
}
