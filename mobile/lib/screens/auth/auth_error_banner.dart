import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Inline error banner shared by the login and registration screens, so a
/// failed attempt looks and reads the same way everywhere in the auth
/// flow. [message] must already be plain-language — never pass a raw
/// exception or HTTP status into this widget.
class AuthErrorBanner extends StatelessWidget {
  final String message;
  const AuthErrorBanner({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.chili.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.chili.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: AppColors.chili, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(color: AppColors.chili, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
