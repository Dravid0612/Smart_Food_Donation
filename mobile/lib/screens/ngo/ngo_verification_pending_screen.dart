import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';

/// Shown instead of the normal NGO dashboard whenever the signed-in NGO's
/// verified status is false — right after registration, or on any later
/// login while an admin review is still pending.
///
/// This screen intentionally has no bottom navigation: an unverified NGO
/// has nothing else it's allowed to do yet.
class NgoVerificationPendingScreen extends StatelessWidget {
  final String organisationName;
  final VoidCallback onLogout;
  final Future<void> Function()? onRefreshStatus;

  const NgoVerificationPendingScreen({
    super.key,
    required this.organisationName,
    required this.onLogout,
    this.onRefreshStatus,
  });

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: AppLocale.code,
      builder: (context, _, __) => Scaffold(
        backgroundColor: AppColors.leafMist,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: const BoxDecoration(
                      color: AppColors.marigold,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.schedule_outlined,
                        color: Colors.white, size: 28),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    AppLocale.t('verification_pending'),
                    style: AppTextStyles.h2,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    AppLocale.t('verification_pending_title'),
                    style: AppTextStyles.body.copyWith(
                      color: AppColors.deepSabzi,
                      fontWeight: FontWeight.w600,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    AppLocale.t('verification_pending_body')
                        .replaceAll('{name}', organisationName),
                    style: AppTextStyles.bodySmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  if (onRefreshStatus != null)
                    OutlinedButton(
                      onPressed: onRefreshStatus,
                      child: Text(AppLocale.t('check_status')),
                    ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () {},
                    child: const Text('CONTACT SUPPORT'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: onLogout,
                    child: Text(
                      AppLocale.t('log_out'),
                      style: const TextStyle(color: AppColors.sageGrey),
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
}
