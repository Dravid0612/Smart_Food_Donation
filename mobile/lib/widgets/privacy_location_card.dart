import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Explicit privacy card that never silently hides data, but displays clear blurred/locked states
/// before authorization and reveals full address only after NGO acceptance / volunteer assignment.
class PrivacyLocationCard extends StatelessWidget {
  final String locationText;
  final bool isExact;
  final String? contactName;
  final String? contactPhone;

  const PrivacyLocationCard({
    super.key,
    required this.locationText,
    this.isExact = false,
    this.contactName,
    this.contactPhone,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(
          color: isExact ? AppTheme.primaryGreen.withValues(alpha: 0.3) : AppTheme.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isExact ? Icons.location_on : Icons.lock_outline,
                color: isExact ? AppTheme.primaryGreen : AppTheme.secondaryTerracotta,
                size: 20,
              ),
              const SizedBox(width: AppTheme.space8),
              Text(
                isExact ? context.tr('pickup_address') : '${context.tr('pickup_address')} (${context.tr('role_donor')})',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: 2),
                decoration: BoxDecoration(
                  color: isExact ? AppTheme.success.withValues(alpha: 0.1) : AppTheme.warning.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                ),
                child: Text(
                  isExact ? context.tr('verified').toUpperCase() : context.tr('unverified').toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: isExact ? AppTheme.success : AppTheme.warning,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          Text(
            locationText.isNotEmpty ? locationText : context.tr('pickup_address'),
            style: TextStyle(
              fontSize: 15,
              fontWeight: isExact ? FontWeight.w600 : FontWeight.normal,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: AppTheme.space8),
          if (!isExact)
            Row(
              children: [
                const Icon(Icons.info_outline, size: 14, color: AppTheme.textSecondary),
                const SizedBox(width: AppTheme.space4),
                Expanded(
                  child: Text(
                    context.tr('why_match'),
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                ),
              ],
            )
          else if (contactName != null || contactPhone != null) ...[
            const Divider(color: AppTheme.border, height: AppTheme.space16),
            Row(
              children: [
                const Icon(Icons.person_outline, size: 16, color: AppTheme.textSecondary),
                const SizedBox(width: AppTheme.space4),
                Text(
                  contactName ?? context.tr('role_donor'),
                  style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary, fontWeight: FontWeight.w500),
                ),
                if (contactPhone != null) ...[
                  const Spacer(),
                  const Icon(Icons.phone_outlined, size: 16, color: AppTheme.primaryGreen),
                  const SizedBox(width: AppTheme.space4),
                  Text(
                    contactPhone!,
                    style: const TextStyle(fontSize: 13, color: AppTheme.primaryGreen, fontWeight: FontWeight.bold),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
