import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/theme/app_theme.dart';
import '../../core/localization/app_locale.dart';
import '../../core/api/api_client.dart';
import '../../providers/auth_provider.dart';

/// Phone Verification Screen — Smart Food Rescue
/// Allows authenticated users to verify their phone number via OTP SMS.
///
/// Flow:
///   1. Enter phone number + country code
///   2. Tap "Send Code" → POST /api/auth/phone/send-verification
///   3. Enter 6-digit OTP
///   4. Tap "Verify" → POST /api/auth/phone/verify
///   5. On success: phone_verified = true in user profile
class PhoneVerificationScreen extends StatefulWidget {
  const PhoneVerificationScreen({super.key});

  @override
  State<PhoneVerificationScreen> createState() => _PhoneVerificationScreenState();
}

class _PhoneVerificationScreenState extends State<PhoneVerificationScreen> {
  final _phoneController = TextEditingController();
  final _otpController = TextEditingController();
  final _phoneFocus = FocusNode();
  final _otpFocus = FocusNode();

  String _selectedCountryCode = '+91';
  bool _codeSent = false;
  bool _isSending = false;
  bool _isVerifying = false;
  bool _isVerified = false;

  // Resend countdown
  int _resendCountdown = 0;
  Timer? _resendTimer;

  String? _phoneMasked;
  String? _errorMessage;

  final List<String> _countryCodes = ['+91', '+1', '+44', '+971', '+65', '+61'];

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    _phoneFocus.dispose();
    _otpFocus.dispose();
    _resendTimer?.cancel();
    super.dispose();
  }

  Future<void> _sendVerificationCode() async {
    final phone = _phoneController.text.trim();
    if (phone.isEmpty) {
      setState(() => _errorMessage = 'Please enter your phone number.');
      return;
    }

    setState(() {
      _isSending = true;
      _errorMessage = null;
    });

    try {
      final apiClient = ApiClient();
      final response = await apiClient.dio.post('/auth/phone/send-verification', data: {
        'phone_number': phone,
        'country_code': _selectedCountryCode,
      });

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        setState(() {
          _isSending = false;
          _codeSent = true;
          _phoneMasked = data['phone_masked'] as String?;
          _resendCountdown = 60;
        });
        _startResendCountdown();
        _otpFocus.requestFocus();
      } else {
        setState(() {
          _isSending = false;
          _errorMessage = 'Failed to send verification code. Please try again.';
        });
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        final data = e.response?.data;
        final msg = data is Map ? (data['detail'] as String? ?? 'Please wait before requesting another code.') : 'Rate limited.';
        setState(() {
          _isSending = false;
          _errorMessage = msg;
        });
      } else {
        setState(() {
          _isSending = false;
          _errorMessage = 'Failed to send verification code. Please try again.';
        });
      }
    } catch (e) {
      setState(() {
        _isSending = false;
        _errorMessage = 'Network error. Please check your connection.';
      });
    }
  }

  Future<void> _verifyOtp() async {
    final otp = _otpController.text.trim();
    if (otp.length != 6) {
      setState(() => _errorMessage = 'Please enter the 6-digit code.');
      return;
    }

    setState(() {
      _isVerifying = true;
      _errorMessage = null;
    });

    try {
      final apiClient = ApiClient();
      final response = await apiClient.dio.post('/auth/phone/verify', data: {
        'phone_number': _phoneController.text.trim(),
        'country_code': _selectedCountryCode,
        'otp': otp,
      });

      if (response.statusCode == 200) {
        setState(() {
          _isVerifying = false;
          _isVerified = true;
        });
        if (!mounted) return;
        try {
          await context.read<AuthProvider>().refreshUserProfile();
        } catch (_) {}
        await Future.delayed(const Duration(seconds: 1));
        if (mounted) context.pop();
      } else {
        setState(() {
          _isVerifying = false;
          _errorMessage = 'Verification failed. Please try again.';
        });
      }
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      if (code == 400) {
        setState(() {
          _isVerifying = false;
          _errorMessage = 'Incorrect code. Please try again.';
        });
      } else if (code == 410) {
        setState(() {
          _isVerifying = false;
          _errorMessage = 'This code has expired. Please request a new one.';
          _codeSent = false;
        });
      } else if (code == 409) {
        setState(() {
          _isVerifying = false;
          _errorMessage = 'This code has already been used. Please request a new one.';
          _codeSent = false;
        });
      } else {
        setState(() {
          _isVerifying = false;
          _errorMessage = 'Verification failed. Please try again.';
        });
      }
    } catch (e) {
      setState(() {
        _isVerifying = false;
        _errorMessage = 'Network error. Please check your connection.';
      });
    }
  }

  void _startResendCountdown() {
    _resendTimer?.cancel();
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _resendCountdown--;
        if (_resendCountdown <= 0) {
          _resendCountdown = 0;
          timer.cancel();
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.card,
        title: Text(
          context.tr('phone_verify_title'),
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 16),

              // ── Icon ─────────────────────────────────────────────
              Center(
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(Icons.verified_user, color: Colors.white, size: 40),
                ),
              ),
              const SizedBox(height: 24),

              // ── Title + Subtitle ──────────────────────────────────
              Center(
                child: Text(
                  context.tr('phone_verify_title'),
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Center(
                child: Text(
                  context.tr('phone_verify_subtitle'),
                  style: const TextStyle(color: AppTheme.textSecondary),
                  textAlign: TextAlign.center,
                ),
              ),

              const SizedBox(height: 32),

              // ── Success Banner ────────────────────────────────────
              if (_isVerified)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF86EFAC)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle, color: Color(0xFF16A34A), size: 24),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          context.tr('phone_verified'),
                          style: const TextStyle(
                            color: Color(0xFF15803D),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                )
              else ...[

              // ── Phone Input ───────────────────────────────────────
              Row(
                children: [
                  // Country code picker
                  Container(
                    decoration: BoxDecoration(
                      color: AppTheme.card,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.border),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _selectedCountryCode,
                        items: _countryCodes.map((code) => DropdownMenuItem(
                          value: code,
                          child: Text(code, style: const TextStyle(fontWeight: FontWeight.bold)),
                        )).toList(),
                        onChanged: (v) => setState(() => _selectedCountryCode = v!),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _phoneController,
                      focusNode: _phoneFocus,
                      keyboardType: TextInputType.phone,
                      enabled: !_codeSent,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: InputDecoration(
                        labelText: 'Phone Number',
                        hintText: '9876543210',
                        filled: true,
                        fillColor: AppTheme.card,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: const OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(12)),
                          borderSide: BorderSide(color: AppTheme.border),
                        ),
                        prefixIcon: const Icon(Icons.phone_outlined),
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 16),

              if (!_codeSent) ...[
                // ── Send Code Button ────────────────────────────────
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _isSending ? null : _sendVerificationCode,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryGreen,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: _isSending
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : Text(context.tr('verify_phone_action')),
                  ),
                ),
              ] else ...[

              // ── OTP Input ─────────────────────────────────────────
              if (_phoneMasked != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    '${context.tr('otp_sent_to')}: $_phoneMasked',
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                  ),
                ),

              TextFormField(
                controller: _otpController,
                focusNode: _otpFocus,
                keyboardType: TextInputType.number,
                maxLength: 6,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 28, letterSpacing: 8, fontWeight: FontWeight.bold),
                decoration: InputDecoration(
                  labelText: context.tr('phone_verify_enter_code'),
                  counterText: '',
                  filled: true,
                  fillColor: AppTheme.card,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                  enabledBorder: const OutlineInputBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                    borderSide: BorderSide(color: AppTheme.border),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // ── Verify Button ─────────────────────────────────────
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isVerifying ? null : _verifyOtp,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryGreen,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: _isVerifying
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : Text(context.tr('phone_verify_title')),
                ),
              ),

              const SizedBox(height: 12),

              // ── Resend ────────────────────────────────────────────
              Center(
                child: TextButton(
                  onPressed: _resendCountdown > 0 ? null : () {
                    setState(() {
                      _codeSent = false;
                      _otpController.clear();
                      _errorMessage = null;
                    });
                  },
                  child: Text(
                    _resendCountdown > 0
                        ? '${context.tr('otp_resend')} (${_resendCountdown}s)'
                        : context.tr('otp_resend'),
                    style: TextStyle(
                      color: _resendCountdown > 0 ? AppTheme.textSecondary : AppTheme.primaryGreen,
                    ),
                  ),
                ),
              ),

              ], // end _codeSent

              ], // end !_isVerified

              // ── Error Message ─────────────────────────────────────
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEE2E2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFCA5A5)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(color: Color(0xFFB91C1C), fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
