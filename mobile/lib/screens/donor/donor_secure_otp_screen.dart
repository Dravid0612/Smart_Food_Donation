import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';

/// Dedicated Secure Pickup Verification Screen
/// Displays server-generated 6-digit OTP exclusively to the verified donor
/// with a live countdown timer, full-screen presentation mode, and server regeneration.
class DonorSecureOtpScreen extends StatefulWidget {
  final int donationId;

  const DonorSecureOtpScreen({super.key, required this.donationId});

  @override
  State<DonorSecureOtpScreen> createState() => _DonorSecureOtpScreenState();
}

class _DonorSecureOtpScreenState extends State<DonorSecureOtpScreen> {
  String? _otpCode;
  String? _otpStatus;
  DateTime? _otpExpiry;
  bool _isLoading = true;
  bool _isRegenerating = false;
  String? _errorMessage;
  Timer? _countdownTimer;
  Duration _timeRemaining = Duration.zero;
  bool _isExpired = false;

  @override
  void initState() {
    super.initState();
    _fetchVerificationCode();
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchVerificationCode() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final provider = Provider.of<DonationProvider>(context, listen: false);
    final data = await provider.fetchVerificationCode(widget.donationId);

    if (!mounted) return;

    if (data != null && data['otp'] != null) {
      final code = data['otp'].toString();
      final status = data['otp_status']?.toString() ?? 'active';
      DateTime? expiry;
      if (data['otp_expiry'] != null) {
        expiry = DateTime.tryParse(data['otp_expiry'].toString())?.toLocal();
      }

      setState(() {
        _otpCode = code;
        _otpStatus = status;
        _otpExpiry = expiry;
        _isLoading = false;
      });

      _startCountdown();
    } else {
      setState(() {
        _errorMessage = provider.errorMessage ?? 'Unable to load verification code.';
        _isLoading = false;
      });
    }
  }

  void _startCountdown() {
    _countdownTimer?.cancel();

    if (_otpExpiry == null) {
      setState(() {
        _timeRemaining = const Duration(minutes: 15);
        _isExpired = false;
      });
      return;
    }

    void updateRemaining() {
      final now = DateTime.now();
      final diff = _otpExpiry!.difference(now);

      if (diff.isNegative || diff.inSeconds <= 0) {
        setState(() {
          _timeRemaining = Duration.zero;
          _isExpired = true;
        });
        _countdownTimer?.cancel();
      } else {
        setState(() {
          _timeRemaining = diff;
          _isExpired = false;
        });
      }
    }

    updateRemaining();
    if (!_isExpired) {
      _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) {
          updateRemaining();
        }
      });
    }
  }

  Future<void> _handleRegenerateOtp() async {
    setState(() => _isRegenerating = true);

    final provider = Provider.of<DonationProvider>(context, listen: false);
    final data = await provider.regenerateOtp(widget.donationId);

    if (!mounted) return;

    setState(() => _isRegenerating = false);

    if (data != null && data['otp'] != null) {
      final code = data['otp'].toString();
      final status = data['otp_status']?.toString() ?? 'active';
      DateTime? expiry;
      if (data['otp_expiry'] != null) {
        expiry = DateTime.tryParse(data['otp_expiry'].toString())?.toLocal();
      }

      setState(() {
        _otpCode = code;
        _otpStatus = status;
        _otpExpiry = expiry;
      });

      _startCountdown();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.tr('code_refreshed')),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(provider.errorMessage != null ? context.trError(provider.errorMessage!) : 'Error regenerating OTP'),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _openFullScreenShowMode(BuildContext context, String code) {
    showDialog(
      context: context,
      useSafeArea: false,
      builder: (ctx) => Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryGreen.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.primaryGreen),
                      ),
                      child: Text(
                        context.tr('pickup_verification').toUpperCase(),
                        style: const TextStyle(
                          color: AppTheme.primaryGreen,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.0,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white, size: 28),
                      onPressed: () => Navigator.of(ctx).pop(),
                    ),
                  ],
                ),
                Column(
                  children: [
                    Text(
                      context.tr('show_code_to_volunteer'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Color(0xFFE2E8F0),
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 36),
                    // Giant High-Contrast Digit Layout
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 28),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.primaryGreen, width: 3),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primaryGreen.withValues(alpha: 0.3),
                            blurRadius: 24,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: code.split('').map((char) {
                          return Container(
                            margin: const EdgeInsets.symmetric(horizontal: 5),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF1E293B),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              char,
                              style: const TextStyle(
                                fontSize: 48,
                                fontWeight: FontWeight.w900,
                                color: AppTheme.primaryGreen,
                                letterSpacing: 2.0,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      context.tr('code_expires_in', {'time': _formatDuration(_timeRemaining)}),
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    onPressed: () => Navigator.of(ctx).pop(),
                    icon: const Icon(Icons.arrow_back, color: Colors.white),
                    label: Text(
                      context.tr('close'),
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF334155),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isConsumed = _otpStatus == 'consumed' || _otpCode == 'USED';

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(
          context.tr('pickup_verification'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textPrimary),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: context.tr('refresh'),
            onPressed: _fetchVerificationCode,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryGreen))
          : _errorMessage != null
              ? _buildErrorState()
              : SafeArea(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppTheme.space20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        // Security Badge Header
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                            border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.lock_rounded, color: AppTheme.primaryGreen, size: 16),
                              const SizedBox(width: 8),
                              Text(
                                context.tr('pickup_verification').toUpperCase(),
                                style: const TextStyle(
                                  color: AppTheme.primaryGreen,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1.0,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppTheme.space16),

                        // Title and Instructions
                        Text(
                          context.tr('show_code_to_volunteer'),
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textPrimary,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: AppTheme.space8),
                        Text(
                          context.tr('handover_confirmed_desc'),
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppTheme.textSecondary,
                            height: 1.4,
                          ),
                        ),
                        const SizedBox(height: AppTheme.space24),

                        // Prominent 6-Digit OTP Card
                        _buildOtpCard(context, isConsumed),
                        const SizedBox(height: AppTheme.space20),

                        // Expiry Timer or Expiration Notice
                        _buildExpiryIndicator(isConsumed),
                        const SizedBox(height: AppTheme.space28),

                        // Primary Actions
                        if (!isConsumed && !_isExpired && _otpCode != null && _otpCode != 'USED') ...[
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: ElevatedButton.icon(
                              onPressed: () => _openFullScreenShowMode(context, _otpCode!),
                              icon: const Icon(Icons.fullscreen, color: Colors.white, size: 22),
                              label: Text(
                                context.tr('show_to_volunteer'),
                                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.primaryGreen,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppTheme.space12),
                        ],

                        // Request New Code Button (when expired or requested)
                        if (_isExpired || isConsumed) ...[
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: OutlinedButton.icon(
                              onPressed: _isRegenerating ? null : _handleRegenerateOtp,
                              icon: _isRegenerating
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primaryGreen),
                                    )
                                  : const Icon(Icons.refresh_rounded, color: AppTheme.primaryGreen),
                              label: Text(
                                _isRegenerating ? context.tr('loading') : context.tr('request_new_code'),
                                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                              ),
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(color: AppTheme.primaryGreen, width: 1.5),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppTheme.space12),
                        ],

                        // Close / Back Button
                        SizedBox(
                          width: double.infinity,
                          height: 46,
                          child: TextButton(
                            onPressed: () => context.pop(),
                            child: Text(
                              context.tr('close'),
                              style: const TextStyle(fontSize: 14, color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ),
                        const SizedBox(height: AppTheme.space20),

                        // Security Assurance Note
                        Container(
                          padding: const EdgeInsets.all(AppTheme.space14),
                          decoration: BoxDecoration(
                            color: AppTheme.card,
                            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                            border: Border.all(color: AppTheme.border),
                            boxShadow: AppTheme.shadowCard,
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.verified_user_outlined, color: AppTheme.primaryGreen, size: 20),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  context.tr('otp_donor_instruction', {'otp': _otpCode ?? '••••••'}),
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppTheme.textSecondary,
                                    height: 1.4,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildOtpCard(BuildContext context, bool isConsumed) {
    final code = _otpCode ?? '------';
    final digits = code.split('');

    return Semantics(
      label: context.tr('semantic_otp_code', {'digits': digits.join(' ')}),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space24),
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
          border: Border.all(
            color: isConsumed
                ? AppTheme.border
                : _isExpired
                    ? AppTheme.error
                    : AppTheme.primaryGreen,
            width: 2,
          ),
          boxShadow: AppTheme.shadowCard,
        ),
        child: Column(
          children: [
            Text(
              context.tr('secure_pickup_code').toUpperCase(),
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 11,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: AppTheme.space20),
            if (isConsumed)
              const Text(
                'VERIFIED / USED',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textMuted,
                  letterSpacing: 2,
                ),
              )
            else
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: digits.map((char) {
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.background,
                      borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                      border: Border.all(
                        color: _isExpired ? AppTheme.error.withValues(alpha: 0.5) : AppTheme.primaryGreen.withValues(alpha: 0.5),
                        width: 1.5,
                      ),
                    ),
                    child: Text(
                      char,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        color: _isExpired ? AppTheme.error : AppTheme.textPrimary,
                        letterSpacing: 1.0,
                      ),
                    ),
                  );
                }).toList(),
              ),
            const SizedBox(height: AppTheme.space16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                digits.length,
                (i) => Container(
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: isConsumed
                        ? AppTheme.textMuted
                        : _isExpired
                            ? AppTheme.error
                            : AppTheme.primaryGreen,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExpiryIndicator(bool isConsumed) {
    if (isConsumed) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(color: AppTheme.border),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_outline, color: AppTheme.primaryGreen, size: 18),
            const SizedBox(width: 8),
            Text(
              context.tr('status_collected'),
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
    }

    if (_isExpired) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: AppTheme.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.timer_off_outlined, color: AppTheme.error, size: 18),
            const SizedBox(width: 8),
            Text(
              context.tr('verification_code_expired'),
              style: const TextStyle(color: AppTheme.error, fontSize: 13, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.info.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
        border: Border.all(color: AppTheme.info.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.timer_outlined, color: AppTheme.info, size: 18),
          const SizedBox(width: 8),
          Text(
            context.tr('code_expires_in', {'time': _formatDuration(_timeRemaining)}),
            style: const TextStyle(
              color: AppTheme.info,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppTheme.error),
            const SizedBox(height: 16),
            Text(
              context.tr('unable_load_otp'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage ?? '',
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _fetchVerificationCode,
              icon: const Icon(Icons.refresh, color: Colors.white),
              label: Text(context.tr('retry'), style: const TextStyle(color: Colors.white)),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryGreen,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
