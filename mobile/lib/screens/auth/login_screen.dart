import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../core/models/auth_models.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/auth/app_text_field.dart';
import '../../widgets/auth/auth_error_banner.dart';
import '../../widgets/auth/role_selector.dart';

/// Single login screen shared by all four roles:
/// Donor, NGO, Volunteer, Admin.
///
/// Features a compact role selector. Role selection is NOT permission:
/// the backend determines the actual authenticated role. If the selected
/// role does not match the authenticated account role, the login context
/// is rejected and a clear message is displayed ("These credentials belong to an {role} account.").
class LoginScreen extends StatefulWidget {
  final Future<AuthResult> Function(String identifier, String password)?
      onLogin;
  final VoidCallback? onForgotPassword;
  final VoidCallback? onNavigateToRegister;
  final UserRole? initialRole;
  final Future<void> Function()? onRejectSession;
  final void Function(String route)? onRoleRouted;

  final String donorHomeRoute;
  final String ngoHomeRoute;
  final String ngoPendingRoute;
  final String volunteerHomeRoute;
  final String adminHomeRoute;

  const LoginScreen({
    super.key,
    this.onLogin,
    this.onForgotPassword,
    this.onNavigateToRegister,
    this.initialRole,
    this.onRejectSession,
    this.onRoleRouted,
    this.donorHomeRoute = '/donor',
    this.ngoHomeRoute = '/ngo',
    this.ngoPendingRoute = '/ngo/pending',
    this.volunteerHomeRoute = '/volunteer',
    this.adminHomeRoute = '/admin',
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _identifierController = TextEditingController();
  final _passwordController = TextEditingController();

  UserRole? _selectedRole;
  bool _rememberMe = true;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _selectedRole = widget.initialRole;
  }

  @override
  void dispose() {
    _identifierController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// Best-effort mapping from a raw backend error string to a localized
  /// one.
  String _localizeAuthError(String rawMessage) {
    const knownErrors = {
      'Invalid credentials.': 'invalid_credentials',
      'Invalid credentials': 'invalid_credentials',
    };
    final key = knownErrors[rawMessage.trim()];
    return key != null ? AppLocale.t(key) : rawMessage;
  }

  Future<void> _submit() async {
    setState(() => _errorMessage = null);
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);
    try {
      final onLoginFn = widget.onLogin ??
          (id, pw) async => AuthResult(
                role: _selectedRole ?? UserRole.donor,
                displayName: 'User',
              );
      final result = await onLoginFn(
        _identifierController.text.trim(),
        _passwordController.text,
      );
      if (!mounted) return;

      // Role selection is NOT permission — backend determines true role.
      // If the selected role does not match the actual authenticated account:
      // reject the login context and show a clear message.
      if (_selectedRole != null && _selectedRole != result.role) {
        if (widget.onRejectSession != null) {
          await widget.onRejectSession!();
        }
        if (!mounted) return;
        setState(() {
          _errorMessage = AppLocale.roleMismatchMessage(result.role);
          _isSubmitting = false;
        });
        return;
      }

      _routeAfterAuth(result);
    } on AuthException catch (e) {
      setState(() => _errorMessage = _localizeAuthError(e.message));
    } catch (_) {
      setState(() => _errorMessage = AppLocale.t('network_error_login'));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  void _routeAfterAuth(AuthResult result) {
    final String route;
    switch (result.role) {
      case UserRole.donor:
        route = widget.donorHomeRoute;
        break;
      case UserRole.volunteer:
        route = widget.volunteerHomeRoute;
        break;
      case UserRole.admin:
        route = widget.adminHomeRoute;
        break;
      case UserRole.ngo:
        route =
            result.ngoVerified ? widget.ngoHomeRoute : widget.ngoPendingRoute;
        break;
    }
    if (widget.onRoleRouted != null) {
      widget.onRoleRouted!(route);
      return;
    }
    try {
      Navigator.of(context).pushNamedAndRemoveUntil(route, (r) => false);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    // Rebuilding on AppLocale.code is what actually makes the language
    // switch work — every string below is read fresh from AppLocale.t()
    // each time this fires, so there is no separate "selected language"
    // state to fall out of sync with what's on screen.
    return ValueListenableBuilder<String>(
      valueListenable: AppLocale.code,
      builder: (context, _, __) => Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Align(
                    alignment: Alignment.centerRight,
                    child: _LanguageSelector(),
                  ),
                  const SizedBox(height: 12),
                  Center(
                    child: Column(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: AppColors.sabziGreen,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: const Icon(Icons.eco_outlined,
                              color: Colors.white, size: 24),
                        ),
                        const SizedBox(height: 8),
                        Text(AppLocale.t('app_name'), style: AppTextStyles.h1),
                        const SizedBox(height: 2),
                        Text(
                          AppLocale.t('tagline'),
                          style: AppTextStyles.bodySmall,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  RoleSelector(
                    selected: _selectedRole,
                    onChanged: (role) => setState(
                      () => _selectedRole = (_selectedRole == role ? null : role),
                    ),
                    showAdmin: true,
                  ),
                  const SizedBox(height: 14),
                  if (_errorMessage != null) ...[
                    AuthErrorBanner(message: _errorMessage!),
                    const SizedBox(height: 10),
                  ],
                  AppTextField(
                    label: AppLocale.t('phone_or_email'),
                    hint: AppLocale.t('phone_or_email_hint'),
                    controller: _identifierController,
                    keyboardType: TextInputType.emailAddress,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return AppLocale.t('enter_phone_or_email');
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 10),
                  AppTextField(
                    label: AppLocale.t('password'),
                    hint: AppLocale.t('enter_password_hint'),
                    controller: _passwordController,
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return AppLocale.t('enter_password');
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: InkWell(
                          borderRadius: BorderRadius.circular(6),
                          onTap: () => setState(() => _rememberMe = !_rememberMe),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: Checkbox(
                                    value: _rememberMe,
                                    activeColor: AppColors.sabziGreen,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    onChanged: (val) => setState(
                                      () => _rememberMe = val ?? true,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    AppLocale.t('remember_me'),
                                    style: AppTextStyles.bodySmall.copyWith(
                                      color: AppColors.deepSabzi,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                    maxLines: 1,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: widget.onForgotPassword ?? () {},
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: Text(
                              AppLocale.t('forgot_password'),
                              style: const TextStyle(
                                color: AppColors.sabziGreen,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: _isSubmitting ? null : _submit,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : Text(AppLocale.t('log_in')),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Expanded(
                          child: Divider(color: AppColors.hairline)),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: Text(AppLocale.t('or'),
                            style: AppTextStyles.bodySmall),
                      ),
                      const Expanded(
                          child: Divider(color: AppColors.hairline)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: widget.onNavigateToRegister ?? () {},
                    child: Text(AppLocale.t('create_account')),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LangOption {
  final String code;
  final String label;
  const _LangOption(this.code, this.label);
}

class _LanguageSelector extends StatelessWidget {
  const _LanguageSelector();

  static const List<_LangOption> _options = [
    _LangOption('en', 'EN'),
    _LangOption('ta', 'TA'),
    _LangOption('hi', 'HI'),
  ];

  @override
  Widget build(BuildContext context) {
    final current = AppLocale.code.value;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: _options.map((option) {
        final bool isSelected = option.code == current;
        return Padding(
          padding: const EdgeInsets.only(left: 6),
          child: GestureDetector(
            onTap: () => AppLocale.setLocale(option.code),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: isSelected ? AppColors.sabziGreen : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                option.label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: isSelected ? Colors.white : AppColors.sageGrey,
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
