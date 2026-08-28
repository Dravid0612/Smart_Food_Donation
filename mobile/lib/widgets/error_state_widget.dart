import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Standard error state widget with retry action and human-friendly error mapping
class ErrorStateWidget extends StatelessWidget {
  final String? title;
  final String message;
  final VoidCallback? onRetry;
  final String? retryLabel;

  const ErrorStateWidget({
    super.key,
    this.title,
    required this.message,
    this.onRetry,
    this.retryLabel,
  });

  /// Map raw error / status code into a human-readable message
  static String formatErrorMessage(BuildContext context, dynamic error) {
    if (error == null) return context.tr('err_server');
    final str = error.toString();
    return context.trError(str);
  }

  @override
  Widget build(BuildContext context) {
    final effectiveTitle = title ?? context.tr('error');
    final effectiveRetry = retryLabel ?? context.tr('retry');

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.error_outline, size: 40, color: AppTheme.error),
            ),
            const SizedBox(height: AppTheme.space16),
            Text(
              effectiveTitle,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppTheme.space8),
            Text(
              context.trError(message),
              style: const TextStyle(
                fontSize: 14,
                color: AppTheme.textSecondary,
                height: 1.4,
              ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppTheme.space24),
              SizedBox(
                height: 44,
                child: ElevatedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh, size: 18),
                  label: Text(effectiveRetry),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryGreen,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

