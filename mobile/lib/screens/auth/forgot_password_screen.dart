import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';

/// Shared Authentication Stack - Forgot Password Screen.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _identifierController = TextEditingController();
  bool _isSubmitting = false;
  bool _isSubmitted = false;

  @override
  void dispose() {
    _identifierController.dispose();
    super.dispose();
  }

  Future<void> _handleReset() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);
    // Simulate API request to send reset instructions
    await Future.delayed(const Duration(milliseconds: 900));

    if (!mounted) return;
    setState(() {
      _isSubmitting = false;
      _isSubmitted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('forgot_password_title'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/login'),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24, vertical: AppTheme.space32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: _isSubmitted ? _buildSuccessView() : _buildFormView(),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFormView() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.lock_reset_rounded,
                size: 48,
                color: AppTheme.primaryGreen,
              ),
            ),
          ),
          const SizedBox(height: AppTheme.space24),
          Text(
            context.tr('forgot_password_title'),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            context.tr('forgot_password_desc'),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 14,
              color: AppTheme.textSecondary,
              height: 1.4,
            ),
          ),
          const SizedBox(height: AppTheme.space32),

          // Identifier input
          TextFormField(
            controller: _identifierController,
            keyboardType: TextInputType.emailAddress,
            decoration: InputDecoration(
              labelText: '${context.tr('email')} / ${context.tr('phone_number')}',
              hintText: 'user@example.com / 9876543210',
              prefixIcon: const Icon(Icons.person_outline),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
              filled: true,
              fillColor: AppTheme.card,
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return context.tr('field_required');
              }
              final text = value.trim();
              final isEmail = text.contains('@') && text.contains('.');
              final isPhone = RegExp(r'^\+?[0-9]{10,13}$').hasMatch(text.replaceAll(' ', ''));
              if (!isEmail && !isPhone) {
                return context.tr('enter_valid_email');
              }
              return null;
            },
          ),
          const SizedBox(height: AppTheme.space24),

          // Submit Button
          ElevatedButton(
            onPressed: _isSubmitting ? null : _handleReset,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryGreen,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
              elevation: 2,
            ),
            child: _isSubmitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                  )
                : Text(
                    context.tr('send_reset_instructions').toUpperCase(),
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                  ),
          ),
          const SizedBox(height: AppTheme.space20),

          // Return to Login
          TextButton(
            onPressed: () => context.canPop() ? context.pop() : context.go('/login'),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.arrow_back, size: 16, color: AppTheme.textSecondary),
                const SizedBox(width: 6),
                Text(
                  context.tr('back_to_login'),
                  style: const TextStyle(color: AppTheme.textSecondary, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Center(
          child: Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.check_circle_outline,
              size: 54,
              color: AppTheme.primaryGreen,
            ),
          ),
        ),
        const SizedBox(height: AppTheme.space24),
        Text(
          context.tr('reset_sent_title'),
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: AppTheme.textPrimary,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          context.tr('reset_sent_desc'),
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 14,
            color: AppTheme.textSecondary,
            height: 1.4,
          ),
        ),
        const SizedBox(height: AppTheme.space32),
        ElevatedButton(
          onPressed: () => context.go('/login'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryGreen,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
            elevation: 2,
          ),
          child: Text(
            context.tr('back_to_login').toUpperCase(),
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 0.5),
          ),
        ),
      ],
    );
  }
}
