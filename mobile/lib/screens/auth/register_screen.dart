import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../core/models/auth_models.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/auth/app_text_field.dart';
import '../../widgets/auth/auth_error_banner.dart';
import '../../widgets/auth/role_selector.dart';

/// Parameters collected on the registration screen and handed to
/// [RegisterScreen.onRegister].
class RegisterRequest {
  final UserRole role;
  final String name;
  final String contact;
  final String password;
  final String extraField;
  final String? phone;
  final String? address;
  final String? adminSecret;
  final int? capacity;
  final String? operatingHours;
  final String? demandRequirements;

  const RegisterRequest({
    required this.role,
    required this.name,
    required this.contact,
    required this.password,
    required this.extraField,
    this.phone,
    this.address,
    this.adminSecret,
    this.capacity,
    this.operatingHours,
    this.demandRequirements,
  });
}

class _VehicleOption {
  final String key;
  final String labelKey;
  const _VehicleOption(this.key, this.labelKey);
}

class RegisterScreen extends StatefulWidget {
  final Future<AuthResult> Function(RegisterRequest request) onRegister;

  final String donorHomeRoute;
  final String volunteerHomeRoute;
  final String ngoPendingRoute;
  final String adminHomeRoute;
  final bool allowAdmin;

  const RegisterScreen({
    super.key,
    required this.onRegister,
    this.donorHomeRoute = '/donor',
    this.volunteerHomeRoute = '/volunteer',
    this.ngoPendingRoute = '/ngo/pending',
    this.adminHomeRoute = '/admin',
    this.allowAdmin = true,
  });

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _contactController = TextEditingController();
  final _passwordController = TextEditingController();
  final _extraController = TextEditingController(); // business/org name or admin secret

  UserRole _role = UserRole.donor;
  String _vehicleKey = 'bike';
  bool _isSubmitting = false;
  String? _errorMessage;

  static const List<_VehicleOption> _vehicleOptions = [
    _VehicleOption('walking', 'vehicle_walking'),
    _VehicleOption('bike', 'vehicle_bike'),
    _VehicleOption('car', 'vehicle_car'),
    _VehicleOption('van', 'vehicle_van'),
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _contactController.dispose();
    _passwordController.dispose();
    _extraController.dispose();
    super.dispose();
  }

  String get _extraLabel {
    switch (_role) {
      case UserRole.donor:
        return AppLocale.t('business_name');
      case UserRole.ngo:
        return AppLocale.t('organisation_name');
      case UserRole.volunteer:
        return AppLocale.t('vehicle_type');
      case UserRole.admin:
        return AppLocale.t('admin_passkey');
    }
  }

  Future<void> _submit() async {
    setState(() => _errorMessage = null);
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);
    try {
      final isEmail = _contactController.text.trim().contains('@');
      final request = RegisterRequest(
        role: _role,
        name: _nameController.text.trim(),
        contact: _contactController.text.trim(),
        password: _passwordController.text,
        extraField: _role == UserRole.volunteer
            ? _vehicleKey
            : _extraController.text.trim(),
        phone: isEmail ? null : _contactController.text.trim(),
        adminSecret: _role == UserRole.admin ? _extraController.text.trim() : null,
      );
      final result = await widget.onRegister(request);
      if (!mounted) return;
      _routeAfterRegister(result);
    } on AuthException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (_) {
      setState(
          () => _errorMessage = AppLocale.t('network_error_register'));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  void _routeAfterRegister(AuthResult result) {
    final String route;
    switch (result.role) {
      case UserRole.donor:
        route = widget.donorHomeRoute;
        break;
      case UserRole.volunteer:
        route = widget.volunteerHomeRoute;
        break;
      case UserRole.ngo:
        route = widget.ngoPendingRoute;
        break;
      case UserRole.admin:
        route = widget.adminHomeRoute;
        break;
    }
    Navigator.of(context).pushNamedAndRemoveUntil(route, (r) => false);
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: AppLocale.code,
      builder: (context, _, __) => Scaffold(
        appBar: AppBar(
          backgroundColor: AppColors.leafMist,
          elevation: 0,
          iconTheme: const IconThemeData(color: AppColors.deepSabzi),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(AppLocale.t('create_account_title'),
                      style: AppTextStyles.h1),
                  const SizedBox(height: 4),
                  Text(AppLocale.t('choose_role'),
                      style: AppTextStyles.bodySmall),
                  const SizedBox(height: 16),
                  RoleSelector(
                    selected: _role,
                    onChanged: (role) => setState(() {
                      _role = role;
                      _extraController.clear();
                    }),
                    showAdmin: widget.allowAdmin,
                  ),
                  const SizedBox(height: 20),
                  if (_errorMessage != null) ...[
                    AuthErrorBanner(message: _errorMessage!),
                    const SizedBox(height: 12),
                  ],
                  AppTextField(
                    label: AppLocale.t('full_name'),
                    hint: AppLocale.t('full_name_hint'),
                    controller: _nameController,
                    validator: (v) => (v == null || v.trim().isEmpty)
                        ? AppLocale.t('enter_name')
                        : null,
                  ),
                  const SizedBox(height: 14),
                  AppTextField(
                    label: AppLocale.t('phone_or_email'),
                    hint: AppLocale.t('contact_hint'),
                    controller: _contactController,
                    keyboardType: TextInputType.emailAddress,
                    validator: (v) => (v == null || v.trim().isEmpty)
                        ? AppLocale.t('enter_contact')
                        : null,
                  ),
                  const SizedBox(height: 14),
                  AppTextField(
                    label: AppLocale.t('password'),
                    hint: AppLocale.t('create_password_hint'),
                    controller: _passwordController,
                    obscureText: true,
                    validator: (v) {
                      if (v == null || v.isEmpty) {
                        return AppLocale.t('create_password_hint');
                      }
                      if (v.length < 8) {
                        return AppLocale.t('password_min_length');
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 14),
                  if (_role == UserRole.volunteer)
                    _VehicleSelector(
                      selectedKey: _vehicleKey,
                      options: _vehicleOptions,
                      onChanged: (key) => setState(() => _vehicleKey = key),
                    )
                  else if (_role == UserRole.admin)
                    AppTextField(
                      label: AppLocale.t('admin_passkey'),
                      hint: AppLocale.t('admin_passkey_hint'),
                      controller: _extraController,
                      obscureText: true,
                      validator: (v) => (v == null || v.trim().isEmpty)
                          ? AppLocale.t('admin_required')
                          : null,
                    )
                  else
                    AppTextField(
                      label: _extraLabel,
                      hint: _role == UserRole.donor
                          ? AppLocale.t('business_name_hint')
                          : AppLocale.t('organisation_name_hint'),
                      controller: _extraController,
                      validator: (v) => (v == null || v.trim().isEmpty)
                          ? AppLocale.t('field_required')
                          : null,
                    ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _isSubmitting ? null : _submit,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : Text(AppLocale.t('create_account')),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _VehicleSelector extends StatelessWidget {
  final String selectedKey;
  final List<_VehicleOption> options;
  final ValueChanged<String> onChanged;

  const _VehicleSelector({
    required this.selectedKey,
    required this.options,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(AppLocale.t('vehicle_type'), style: AppTextStyles.label),
        const SizedBox(height: 6),
        Row(
          children: options.map((option) {
            final bool isSelected = option.key == selectedKey;
            return Expanded(
              child: Padding(
                padding: const EdgeInsets.only(right: 6),
                child: GestureDetector(
                  onTap: () => onChanged(option.key),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.sabziGreen
                          : AppColors.surfaceWhite,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isSelected
                            ? AppColors.sabziGreen
                            : AppColors.hairline,
                      ),
                    ),
                    child: Text(
                      AppLocale.t(option.labelKey),
                      style: AppTextStyles.bodySmall.copyWith(
                        color: isSelected ? Colors.white : AppColors.deepSabzi,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
