import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Contextual empty state widget with clear explanation and optional action
class EmptyStateWidget extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? description;
  final String? subtitle;
  final String? actionLabel;
  final String? actionText;
  final VoidCallback? onAction;
  final VoidCallback? onActionPressed;

  const EmptyStateWidget({
    super.key,
    this.icon = Icons.inbox_outlined,
    required this.title,
    this.description,
    this.subtitle,
    this.actionLabel,
    this.actionText,
    this.onAction,
    this.onActionPressed,
  });

  @override
  Widget build(BuildContext context) {
    final textDesc = description ?? subtitle ?? 'No items found.';
    final textAction = actionLabel ?? actionText;
    final callbackAction = onAction ?? onActionPressed;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(AppTheme.space24),
              decoration: BoxDecoration(
                color: AppTheme.primaryGreen.withValues(alpha: 0.06),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 48, color: AppTheme.primaryGreen),
            ),
            const SizedBox(height: AppTheme.space24),
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppTheme.space8),
            Text(
              textDesc,
              style: const TextStyle(
                fontSize: 14,
                color: AppTheme.textSecondary,
                height: 1.4,
              ),
              textAlign: TextAlign.center,
            ),
            if (textAction != null && callbackAction != null) ...[
              const SizedBox(height: AppTheme.space24),
              SizedBox(
                height: 46,
                child: ElevatedButton(
                  onPressed: callbackAction,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryGreen,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppTheme.radiusButton),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24),
                  ),
                  child: Text(textAction),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
