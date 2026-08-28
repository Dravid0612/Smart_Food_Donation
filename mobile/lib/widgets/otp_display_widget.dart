import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Displays a large OTP code for the donor to show the volunteer at pickup.
/// The volunteer enters this OTP to verify the pickup.
class OtpDisplayWidget extends StatelessWidget {
  final String otp;
  final String? label;

  const OtpDisplayWidget({
    super.key,
    required this.otp,
    this.label,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveLabel = label ?? context.trOtpDonor(otp);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF047857), Color(0xFF10B981)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF10B981).withValues(alpha: 0.3),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          const Icon(Icons.lock_open_rounded, color: Colors.white70, size: 28),
          const SizedBox(height: 8),
          Text(
            effectiveLabel,
            style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.3),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: otp.split('').map((digit) {
              return Container(
                width: 44,
                height: 58,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Center(
                  child: Text(
                    digit,
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF047857),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 12),
          TextButton.icon(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: otp));
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(context.tr('success')),
                  duration: const Duration(seconds: 1),
                  backgroundColor: AppTheme.primaryGreen,
                ),
              );
            },
            icon: const Icon(Icons.copy, color: Colors.white70, size: 16),
            label: Text(context.tr('verification_code'), style: const TextStyle(color: Colors.white70, fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
