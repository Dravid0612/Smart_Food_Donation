import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/app_theme.dart';
import '../../core/localization/app_locale.dart';
import '../../services/otp_service.dart';
import '../../widgets/otp_delivery_status_widget.dart';

/// Secure full-screen OTP display for donors.
///
/// SECURITY:
/// - Screen only accessible by authenticated donor.
/// - OTP is shown in an oversized readable format.
/// - Countdown timer shows expiry.
/// - RESEND disabled during rate-limit period.
/// - OTP is NOT captured in screenshots (though Flutter doesn't support secure mode natively).
class PickupOtpScreen extends StatefulWidget {
  final int donationId;
  final String? initialOtp;       // Provided at screen creation (from generate response)
  final DateTime? expiresAt;      // Provided at screen creation
  final String? phoneMasked;
  final String? deliveryStatus;

  const PickupOtpScreen({
    super.key,
    required this.donationId,
    this.initialOtp,
    this.expiresAt,
    this.phoneMasked,
    this.deliveryStatus,
  });

  @override
  State<PickupOtpScreen> createState() => _PickupOtpScreenState();
}

class _PickupOtpScreenState extends State<PickupOtpScreen>
    with WidgetsBindingObserver {
  String? _otp;
  DateTime? _expiresAt;
  String? _phoneMasked;
  String? _deliveryStatus;
  int _remainingSeconds = 0;
  Timer? _countdownTimer;

  bool _isRegenerating = false;
  bool _rateLimited = false;
  String? _errorMessage;
  int _rateLimitCountdown = 0;
  Timer? _rateLimitTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _otp = widget.initialOtp;
    _expiresAt = widget.expiresAt;
    _phoneMasked = widget.phoneMasked;
    _deliveryStatus = widget.deliveryStatus;
    if (_expiresAt != null) {
      _startCountdown();
    }
    // If no OTP was passed, load from API
    if (_otp == null) {
      _loadOtpStatus();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _countdownTimer?.cancel();
    _rateLimitTimer?.cancel();
    super.dispose();
  }

  void _startCountdown() {
    _countdownTimer?.cancel();
    _updateRemainingSeconds();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        _updateRemainingSeconds();
      }
    });
  }

  void _updateRemainingSeconds() {
    if (_expiresAt == null) return;
    final now = DateTime.now().toUtc();
    final diff = _expiresAt!.toUtc().difference(now).inSeconds;
    setState(() => _remainingSeconds = diff > 0 ? diff : 0);
    if (_remainingSeconds <= 0) {
      _countdownTimer?.cancel();
    }
  }

  Future<void> _loadOtpStatus() async {
    try {
      final otpService = OtpService();
      final info = await otpService.getPickupOtpStatus(widget.donationId);
      if (mounted) {
        setState(() {
          _phoneMasked = info.phoneMasked;
          _deliveryStatus = info.deliveryStatus;
          _expiresAt = info.expiresAt;
          if (_expiresAt != null) _startCountdown();
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _errorMessage = e.toString());
      }
    }
  }

  Future<void> _onResend() async {
    if (_isRegenerating || _rateLimited) return;
    setState(() {
      _isRegenerating = true;
      _errorMessage = null;
    });
    try {
      final otpService = OtpService();
      final result = await otpService.regeneratePickupOtp(widget.donationId);
      if (mounted) {
        setState(() {
          _otp = result.otp;
          _expiresAt = result.expiresAt;
          _phoneMasked = result.phoneMasked;
          _deliveryStatus = result.deliveryStatus;
          _isRegenerating = false;
        });
        _startCountdown();
      }
    } on RateLimitException catch (e) {
      if (mounted) {
        setState(() {
          _isRegenerating = false;
          _rateLimited = true;
          _rateLimitCountdown = 60;
          _errorMessage = e.message;
        });
        _startRateLimitCountdown();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isRegenerating = false;
          _errorMessage = 'Failed to regenerate code. Please try again.';
        });
      }
    }
  }

  void _startRateLimitCountdown() {
    _rateLimitTimer?.cancel();
    _rateLimitTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _rateLimitCountdown--;
        if (_rateLimitCountdown <= 0) {
          _rateLimited = false;
          _rateLimitCountdown = 0;
          timer.cancel();
        }
      });
    });
  }

  String get _expiryLabel {
    if (_remainingSeconds <= 0) return context.tr('otp_expired_message');
    final m = _remainingSeconds ~/ 60;
    final s = _remainingSeconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  bool get _isExpired => _remainingSeconds <= 0 && _expiresAt != null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: AppTheme.card,
        title: Text(
          context.tr('otp_show_code'),
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 16),

              // ── Header ──────────────────────────────────────────
              Text(
                context.tr('otp_show_code'),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                context.tr('otp_show_fullscreen'),
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                textAlign: TextAlign.center,
              ),

              const SizedBox(height: 32),

              // ── Phone + SMS Status ───────────────────────────────
              if (_phoneMasked != null || _deliveryStatus != null) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.card,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    children: [
                      if (_phoneMasked != null) ...[
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.phone, size: 16, color: AppTheme.textSecondary),
                            const SizedBox(width: 8),
                            Text(
                              '${context.tr('otp_sent_to')}: $_phoneMasked',
                              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                      ],
                      OtpDeliveryStatusWidget(status: _deliveryStatus),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],

              // ── OTP Display ──────────────────────────────────────
              Container(
                padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: _isExpired
                        ? [const Color(0xFF374151), const Color(0xFF1F2937)]
                        : [const Color(0xFF1E40AF), const Color(0xFF7C3AED)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [
                    BoxShadow(
                      color: _isExpired
                          ? Colors.black26
                          : const Color(0xFF7C3AED).withValues(alpha: 0.4),
                      blurRadius: 24,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    if (_isExpired)
                      Column(
                        children: [
                          const Icon(Icons.timer_off, color: Colors.white54, size: 48),
                          const SizedBox(height: 12),
                          Text(
                            context.tr('otp_expired_message'),
                            style: const TextStyle(color: Colors.white70, fontSize: 16),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      )
                    else if (_otp != null)
                      _OtpDigitsDisplay(otp: _otp!)
                    else
                      const Column(
                        children: [
                          CircularProgressIndicator(color: Colors.white),
                          SizedBox(height: 16),
                          Text(
                            'Loading code...',
                            style: TextStyle(color: Colors.white70),
                          ),
                        ],
                      ),

                    if (!_isExpired && _expiresAt != null) ...[
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.timer_outlined, color: Colors.white70, size: 16),
                          const SizedBox(width: 6),
                          Text(
                            '${context.tr('otp_expires_in')}: $_expiryLabel',
                            style: TextStyle(
                              color: _remainingSeconds < 60
                                  ? const Color(0xFFFCA5A5)
                                  : Colors.white70,
                              fontSize: 13,
                              fontWeight: _remainingSeconds < 60
                                  ? FontWeight.bold
                                  : FontWeight.normal,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // ── Instruction ──────────────────────────────────────
              const Text(
                'Show this code to the assigned volunteer when they arrive.',
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                textAlign: TextAlign.center,
              ),

              const SizedBox(height: 32),

              // ── Error Message ────────────────────────────────────
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEE2E2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFCA5A5)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded, color: Color(0xFFEF4444), size: 20),
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

              // ── Resend Button ────────────────────────────────────
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: (_isRegenerating || _rateLimited || _isExpired && _otp != null)
                      ? null
                      : _onResend,
                  icon: _isRegenerating
                      ? const SizedBox(
                          width: 18, height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.refresh),
                  label: Text(
                    _rateLimited
                        ? '${context.tr('otp_resend')} (${_rateLimitCountdown}s)'
                        : context.tr('otp_resend'),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _rateLimited
                        ? const Color(0xFF6B7280)
                        : AppTheme.primaryGreen,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // ── Security note ────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0FDF4),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF86EFAC)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.shield_outlined, color: Color(0xFF16A34A), size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Share this code only with the volunteer assigned to your donation.',
                        style: TextStyle(color: Color(0xFF15803D), fontSize: 12),
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
}

/// Displays the 6-digit OTP as individual large digit cards
class _OtpDigitsDisplay extends StatelessWidget {
  final String otp;

  const _OtpDigitsDisplay({required this.otp});

  @override
  Widget build(BuildContext context) {
    final digits = otp.padLeft(6, '0').split('');
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (int i = 0; i < digits.length; i++) ...[
              _DigitCard(digit: digits[i]),
              if (i == 2) const SizedBox(width: 12),
              if (i != digits.length - 1 && i != 2) const SizedBox(width: 8),
            ],
          ],
        ),
        const SizedBox(height: 20),
        // Copy button
        GestureDetector(
          onTap: () {
            Clipboard.setData(ClipboardData(text: otp));
          },
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.copy, size: 14, color: Colors.white54),
              SizedBox(width: 4),
              Text(
                'Copy code',
                style: TextStyle(color: Colors.white54, fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DigitCard extends StatelessWidget {
  final String digit;

  const _DigitCard({required this.digit});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 60,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white30, width: 1),
      ),
      alignment: Alignment.center,
      child: Text(
        digit,
        style: const TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          letterSpacing: 0,
        ),
      ),
    );
  }
}
