import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../models/otp_delivery_model.dart';

/// Reusable SMS delivery status indicator widget.
///
/// Shows one of:
///   ✅ DELIVERED   — green
///   ✓  SENT/UNKNOWN — amber (delivery confirmation unavailable)
///   ❌ FAILED      — red + fallback message
///   📤 QUEUED      — grey sending
///   ⏰ EXPIRED     — grey expired

class OtpDeliveryStatusWidget extends StatelessWidget {
  final String? status;
  final bool compact;

  const OtpDeliveryStatusWidget({
    super.key,
    required this.status,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final display = OtpDeliveryStatusDisplay.fromStatus(status);
    final color = _hexToColor(display.color);

    if (compact) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(display.icon, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 6),
          Text(
            display.label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(display.icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _getLabel(context, display),
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _getDescription(context, display),
                  style: TextStyle(
                    color: color.withValues(alpha: 0.85),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _getLabel(BuildContext context, OtpDeliveryStatusDisplay display) {
    switch (status?.toUpperCase()) {
      case OtpDeliveryStatus.delivered:
        return context.tr('otp_sms_delivered');
      case OtpDeliveryStatus.sent:
      case OtpDeliveryStatus.unknown:
        return context.tr('otp_sms_sent_unconfirmed');
      case OtpDeliveryStatus.failed:
        return context.tr('otp_sms_failed');
      default:
        return display.label;
    }
  }

  String _getDescription(BuildContext context, OtpDeliveryStatusDisplay display) {
    switch (status?.toUpperCase()) {
      case OtpDeliveryStatus.sent:
      case OtpDeliveryStatus.unknown:
        return context.tr('otp_sms_sent_unconfirmed');
      case OtpDeliveryStatus.failed:
        return context.tr('otp_sms_failed');
      default:
        return display.description;
    }
  }

  Color _hexToColor(String hex) {
    final h = hex.replaceFirst('#', '');
    return Color(int.parse('FF$h', radix: 16));
  }
}

/// Compact inline badge version (for donation cards / lists)
class OtpDeliveryStatusBadge extends StatelessWidget {
  final String? status;

  const OtpDeliveryStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    return OtpDeliveryStatusWidget(status: status, compact: true);
  }
}
