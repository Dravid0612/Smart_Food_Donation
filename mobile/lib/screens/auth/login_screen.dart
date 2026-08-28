import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../providers/auth_provider.dart';
import '../../core/theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  // Role-first selection state: null initially until the user taps a role card
  String? _selectedRole; // 'donor', 'ngo', 'volunteer', 'admin'

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _selectRole(String role) {
    if (_selectedRole == role) return;
    setState(() {
      _selectedRole = role;
    });
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final success = await authProvider.login(
      _emailController.text.trim(),
      _passwordController.text,
    );

    if (!mounted) return;

    if (success) {
      final role = authProvider.currentUser?.role ?? _selectedRole ?? 'donor';
      switch (role.toLowerCase()) {
        case 'donor':
          context.go('/donor');
          break;
        case 'ngo':
          context.go('/ngo');
          break;
        case 'volunteer':
          context.go('/volunteer');
          break;
        case 'admin':
          context.go('/admin');
          break;
        default:
          context.go('/donor');
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.trError(authProvider.errorMessage ?? 'Invalid credentials.')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  void _useTestCredentials(String email, String password) {
    _emailController.text = email;
    _passwordController.text = password;
  }

  void _showForgotPasswordDialog() {
    final localeProvider = Provider.of<LocaleProvider>(context, listen: false);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.lock_reset, color: AppTheme.primaryGreen),
            const SizedBox(width: 8),
            Text(context.tr('forgot_password'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ],
        ),
        content: Text(
          localeProvider.currentLanguage == 'ta'
              ? 'உங்கள் கடவுச்சொல்லை மீட்டமைக்க, கணக்கு நிர்வாகியைத் தொடர்பு கொள்ளவும்.'
              : localeProvider.currentLanguage == 'hi'
                  ? 'अपना पासवर्ड रीसेट करने के लिए, कृपया प्लेटफ़ॉर्म व्यवस्थापक से संपर्क करें।'
                  : 'To reset your password, please contact your platform administrator or organization admin.',
          style: const TextStyle(fontSize: 14, height: 1.4),
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryGreen,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Color _getRoleColor(String role) {
    switch (role) {
      case 'donor':
        return const Color(0xFF2F6B4F); // Sabzi Green / Sustainability
      case 'ngo':
        return const Color(0xFF2563EB); // Trust Blue
      case 'volunteer':
        return const Color(0xFFEA580C); // Action Orange
      case 'admin':
        return const Color(0xFF7C3AED); // Security Purple
      default:
        return AppTheme.primaryGreen;
    }
  }

  IconData _getRoleIcon(String role) {
    switch (role) {
      case 'donor':
        return Icons.restaurant;
      case 'ngo':
        return Icons.apartment;
      case 'volunteer':
        return Icons.two_wheeler;
      case 'admin':
        return Icons.security;
      default:
        return Icons.person;
    }
  }

  String _getRoleHeading(String role) {
    switch (role) {
      case 'donor':
        return context.tr('role_donor_login');
      case 'ngo':
        return context.tr('role_ngo_login');
      case 'volunteer':
        return context.tr('role_volunteer_login');
      case 'admin':
        return context.tr('role_admin_login');
      default:
        return context.tr('login');
    }
  }

  String _getRoleSubtitle(String role) {
    switch (role) {
      case 'donor':
        return context.tr('role_donor_login_sub');
      case 'ngo':
        return context.tr('role_ngo_login_sub');
      case 'volunteer':
        return context.tr('role_volunteer_login_sub');
      case 'admin':
        return context.tr('role_admin_login_sub');
      default:
        return context.tr('login_subtitle');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final localeProvider = Provider.of<LocaleProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── Unobtrusive Top Language Switcher ───────────────────────
                  Align(
                    alignment: Alignment.topRight,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.03),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _buildLangChip(localeProvider, 'en', 'EN'),
                          _buildLangChip(localeProvider, 'ta', 'தமிழ்'),
                          _buildLangChip(localeProvider, 'hi', 'हिन्दी'),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),

                  // ── Logo & Header ──────────────────────────────────────────
                  Center(
                    child: Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryGreen,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primaryGreen.withValues(alpha: 0.25),
                            blurRadius: 12,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.volunteer_activism,
                        size: 38,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    context.tr('app_title'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.3,
                      color: Color(0xFF047857),
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    context.tr('tagline'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF475569),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // ── STAGE 1: ROLE SELECTION CARDS (2x2 Grid) ────────────────
                  Row(
                    children: [
                      const Icon(Icons.touch_app_outlined, size: 16, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      Text(
                        context.tr('select_role'),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF334155),
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  Row(
                    children: [
                      Expanded(
                        child: _buildRoleCard(
                          roleKey: 'donor',
                          title: context.trRole('donor'),
                          subtitle: context.tr('role_donor_desc').split('&').first.trim(),
                          icon: Icons.restaurant,
                          color: _getRoleColor('donor'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildRoleCard(
                          roleKey: 'ngo',
                          title: context.trRole('ngo'),
                          subtitle: context.tr('role_ngo_desc').split('&').first.trim(),
                          icon: Icons.apartment,
                          color: _getRoleColor('ngo'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: _buildRoleCard(
                          roleKey: 'volunteer',
                          title: context.trRole('volunteer'),
                          subtitle: context.tr('role_volunteer_desc').split(' ').take(3).join(' '),
                          icon: Icons.two_wheeler,
                          color: _getRoleColor('volunteer'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildRoleCard(
                          roleKey: 'admin',
                          title: context.trRole('admin'),
                          subtitle: context.tr('role_admin_desc'),
                          icon: Icons.security,
                          color: _getRoleColor('admin'),
                        ),
                      ),
                    ],
                  ),

                  // ── STAGE 2: AUTHENTICATION FORM (Expands upon selection) ───
                  AnimatedSize(
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeInOutCubic,
                    child: _selectedRole == null
                        ? const SizedBox.shrink()
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const SizedBox(height: 20),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                decoration: BoxDecoration(
                                  color: _getRoleColor(_selectedRole!).withValues(alpha: 0.08),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: _getRoleColor(_selectedRole!).withValues(alpha: 0.3),
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(8),
                                      decoration: BoxDecoration(
                                        color: _getRoleColor(_selectedRole!),
                                        shape: BoxShape.circle,
                                      ),
                                      child: Icon(
                                        _getRoleIcon(_selectedRole!),
                                        color: Colors.white,
                                        size: 18,
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            _getRoleHeading(_selectedRole!),
                                            style: TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 15,
                                              color: _getRoleColor(_selectedRole!),
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            _getRoleSubtitle(_selectedRole!),
                                            style: const TextStyle(
                                              fontSize: 11,
                                              color: Color(0xFF64748B),
                                              height: 1.3,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 16),

                              // Error Banner
                              if (authProvider.errorMessage != null) ...[
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.red.shade50,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: Colors.red.shade200),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          context.trError(authProvider.errorMessage!),
                                          style: TextStyle(color: Colors.red.shade900, fontSize: 13),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 14),
                              ],

                              // Email Field
                              TextFormField(
                                key: const Key('login_email_field'),
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: InputDecoration(
                                  labelText: context.tr('email'),
                                  prefixIcon: const Icon(Icons.mail_outline, size: 20),
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  filled: true,
                                  fillColor: Colors.white,
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                ),
                                validator: (value) {
                                  if (value == null || value.trim().isEmpty) {
                                    return context.tr('enter_email');
                                  }
                                  if (!value.contains('@') || !value.contains('.')) {
                                    return context.tr('enter_valid_email');
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),

                              // Password Field
                              TextFormField(
                                key: const Key('login_password_field'),
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                decoration: InputDecoration(
                                  labelText: context.tr('password'),
                                  prefixIcon: const Icon(Icons.lock_outline, size: 20),
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  filled: true,
                                  fillColor: Colors.white,
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                  suffixIcon: IconButton(
                                    icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility, size: 20),
                                    onPressed: () {
                                      setState(() => _obscurePassword = !_obscurePassword);
                                    },
                                  ),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return context.tr('enter_password');
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 4),

                              // Forgot Password Action
                              Align(
                                alignment: Alignment.centerRight,
                                child: TextButton(
                                  onPressed: _showForgotPasswordDialog,
                                  child: Text(
                                    context.tr('forgot_password'),
                                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),

                              // Login Button
                              ElevatedButton(
                                key: const Key('login_submit_button'),
                                onPressed: authProvider.isLoading ? null : _handleLogin,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: _getRoleColor(_selectedRole!),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  elevation: 2,
                                ),
                                child: authProvider.isLoading
                                    ? const SizedBox(
                                        height: 20,
                                        width: 20,
                                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                      )
                                    : Text(
                                        context.tr('login').toUpperCase(),
                                        style: const TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 0.5,
                                        ),
                                      ),
                              ),
                              const SizedBox(height: 16),

                              // Role-Specific Register Link (Hidden for Administrator)
                              if (_selectedRole != 'admin') ...[
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      "${context.tr('dont_have_account')} ",
                                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
                                    ),
                                    GestureDetector(
                                      onTap: () => context.push('/register', extra: {'role': _selectedRole}),
                                      child: Text(
                                        context.tr('register'),
                                        style: TextStyle(
                                          color: _getRoleColor(_selectedRole!),
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                              ],

                              // ── Demo 1-Tap Credentials Helper ──────────────────
                              _buildDemoCredentialsBox(),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLangChip(LocaleProvider provider, String langCode, String label) {
    final isSelected = provider.currentLanguage == langCode;
    return GestureDetector(
      onTap: () => provider.setLanguage(langCode),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        margin: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryGreen : Colors.transparent,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? Colors.white : const Color(0xFF64748B),
          ),
        ),
      ),
    );
  }

  Widget _buildRoleCard({
    required String roleKey,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    final isSelected = _selectedRole == roleKey;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        key: Key('role_card_$roleKey'),
        onTap: () => _selectRole(roleKey),
        borderRadius: BorderRadius.circular(14),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? color.withValues(alpha: 0.09) : Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isSelected ? color : color.withValues(alpha: 0.25),
              width: isSelected ? 2.2 : 1.0,
            ),
            boxShadow: [
              BoxShadow(
                color: isSelected ? color.withValues(alpha: 0.15) : Colors.black.withValues(alpha: 0.03),
                blurRadius: isSelected ? 8 : 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      color: isSelected ? color : color.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      icon,
                      color: isSelected ? Colors.white : color,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                            color: isSelected ? color : const Color(0xFF1E293B),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 1),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            fontSize: 9,
                            color: Color(0xFF64748B),
                            height: 1.1,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (isSelected)
                Positioned(
                  top: -6,
                  right: -4,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.check, size: 10, color: Colors.white),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDemoCredentialsBox() {
    final role = _selectedRole ?? 'donor';
    final roleColor = _getRoleColor(role);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.vpn_key_outlined, size: 14, color: roleColor),
              const SizedBox(width: 6),
              Text(
                context.tr('demo_accounts'),
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: roleColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              ActionChip(
                avatar: const Icon(Icons.restaurant, size: 12, color: Color(0xFF2F6B4F)),
                label: Text(context.trRole('donor'), style: const TextStyle(fontSize: 11)),
                backgroundColor: role == 'donor' ? Colors.white : const Color(0xFFF8FAFC),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: role == 'donor' ? const Color(0xFF2F6B4F) : const Color(0xFFCBD5E1)),
                ),
                onPressed: () {
                  _selectRole('donor');
                  _useTestCredentials('donor1@hotel.com', 'pass123');
                },
              ),
              ActionChip(
                avatar: const Icon(Icons.apartment, size: 12, color: Color(0xFF2563EB)),
                label: Text(context.trRole('ngo'), style: const TextStyle(fontSize: 11)),
                backgroundColor: role == 'ngo' ? Colors.white : const Color(0xFFF8FAFC),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: role == 'ngo' ? const Color(0xFF2563EB) : const Color(0xFFCBD5E1)),
                ),
                onPressed: () {
                  _selectRole('ngo');
                  _useTestCredentials('ngo1@greenhope.org', 'pass123');
                },
              ),
              ActionChip(
                avatar: const Icon(Icons.two_wheeler, size: 12, color: Color(0xFFEA580C)),
                label: Text(context.trRole('volunteer'), style: const TextStyle(fontSize: 11)),
                backgroundColor: role == 'volunteer' ? Colors.white : const Color(0xFFF8FAFC),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: role == 'volunteer' ? const Color(0xFFEA580C) : const Color(0xFFCBD5E1)),
                ),
                onPressed: () {
                  _selectRole('volunteer');
                  _useTestCredentials('vol1@volunteer.org', 'pass123');
                },
              ),
              ActionChip(
                avatar: const Icon(Icons.security, size: 12, color: Color(0xFF7C3AED)),
                label: Text(context.trRole('admin'), style: const TextStyle(fontSize: 11)),
                backgroundColor: role == 'admin' ? Colors.white : const Color(0xFFF8FAFC),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: role == 'admin' ? const Color(0xFF7C3AED) : const Color(0xFFCBD5E1)),
                ),
                onPressed: () {
                  _selectRole('admin');
                  _useTestCredentials('admin@fooddonation.org', 'admin123');
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}
