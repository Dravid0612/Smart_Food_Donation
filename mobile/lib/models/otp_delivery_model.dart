/// OTP Delivery Model — Smart Food Rescue
/// Tracks SMS delivery status for pickup OTP and phone verification OTP.
library otp_delivery_model;

class OtpDeliveryStatus {
  static const String queued = 'QUEUED';
  static const String sent = 'SENT';
  static const String delivered = 'DELIVERED';
  static const String failed = 'FAILED';
  static const String expired = 'EXPIRED';
  static const String unknown = 'UNKNOWN';
}

class OtpDeliveryStatusDisplay {
  final String icon;
  final String label;
  final String color; // hex color string
  final String description;

  const OtpDeliveryStatusDisplay({
    required this.icon,
    required this.label,
    required this.color,
    required this.description,
  });

  static OtpDeliveryStatusDisplay fromStatus(String? status) {
    switch (status?.toUpperCase()) {
      case OtpDeliveryStatus.delivered:
        return const OtpDeliveryStatusDisplay(
          icon: '✅',
          label: 'Delivered',
          color: '#10B981',
          description: 'SMS delivered to your verified phone.',
        );
      case OtpDeliveryStatus.sent:
      case OtpDeliveryStatus.unknown:
        return const OtpDeliveryStatusDisplay(
          icon: '✓',
          label: 'Sent',
          color: '#F59E0B',
          description: 'Sent — delivery confirmation unavailable with current provider.',
        );
      case OtpDeliveryStatus.failed:
        return const OtpDeliveryStatusDisplay(
          icon: '⚠',
          label: 'Failed',
          color: '#EF4444',
          description: 'SMS delivery failed. Your secure code is still available in the app.',
        );
      case OtpDeliveryStatus.queued:
        return const OtpDeliveryStatusDisplay(
          icon: '📤',
          label: 'Sending',
          color: '#6B7280',
          description: 'Sending SMS...',
        );
      case OtpDeliveryStatus.expired:
        return const OtpDeliveryStatusDisplay(
          icon: '⏰',
          label: 'Expired',
          color: '#6B7280',
          description: 'This code has expired. Please request a new one.',
        );
      default:
        return const OtpDeliveryStatusDisplay(
          icon: '?',
          label: 'Unknown',
          color: '#6B7280',
          description: 'Delivery status unknown.',
        );
    }
  }
}

/// Model for OTP delivery status API response
class OtpDeliveryInfo {
  final String? deliveryStatus;
  final String? statusDisplay;
  final String? phoneMasked;
  final String? provider;
  final DateTime? sentAt;
  final DateTime? deliveredAt;
  final String? failureReason;
  final bool otpAvailable;
  final int? otpRecordId;
  final DateTime? expiresAt;
  final int? remainingSeconds;
  final String? message;

  const OtpDeliveryInfo({
    this.deliveryStatus,
    this.statusDisplay,
    this.phoneMasked,
    this.provider,
    this.sentAt,
    this.deliveredAt,
    this.failureReason,
    this.otpAvailable = false,
    this.otpRecordId,
    this.expiresAt,
    this.remainingSeconds,
    this.message,
  });

  factory OtpDeliveryInfo.fromJson(Map<String, dynamic> json) {
    return OtpDeliveryInfo(
      deliveryStatus: json['delivery_status'] as String?,
      statusDisplay: json['status_display'] as String?,
      phoneMasked: json['phone_masked'] as String?,
      provider: json['provider'] as String?,
      sentAt: json['sent_at'] != null ? DateTime.tryParse(json['sent_at'] as String) : null,
      deliveredAt: json['delivered_at'] != null ? DateTime.tryParse(json['delivered_at'] as String) : null,
      failureReason: json['failure_reason'] as String?,
      otpAvailable: json['otp_available'] as bool? ?? false,
      otpRecordId: json['otp_record_id'] as int?,
      expiresAt: json['expires_at'] != null ? DateTime.tryParse(json['expires_at'] as String) : null,
      remainingSeconds: json['remaining_seconds'] as int?,
      message: json['message'] as String?,
    );
  }

  OtpDeliveryStatusDisplay get display =>
      OtpDeliveryStatusDisplay.fromStatus(deliveryStatus);

  bool get isDelivered => deliveryStatus == OtpDeliveryStatus.delivered;
  bool get isFailed => deliveryStatus == OtpDeliveryStatus.failed;
  bool get isExpired => deliveryStatus == OtpDeliveryStatus.expired;

  /// Remaining time as formatted string (e.g. "04:23")
  String get remainingFormatted {
    if (remainingSeconds == null || remainingSeconds! <= 0) return '00:00';
    final m = remainingSeconds! ~/ 60;
    final s = remainingSeconds! % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
}

/// Response from regenerate or initial generate endpoint
class PickupOtpGenerateResult {
  final String otp;
  final DateTime expiresAt;
  final int expiresInMinutes;
  final String? deliveryStatus;
  final String? phoneMasked;
  final String? note;
  final String? message;

  const PickupOtpGenerateResult({
    required this.otp,
    required this.expiresAt,
    required this.expiresInMinutes,
    this.deliveryStatus,
    this.phoneMasked,
    this.note,
    this.message,
  });

  factory PickupOtpGenerateResult.fromJson(Map<String, dynamic> json) {
    return PickupOtpGenerateResult(
      otp: json['otp'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
      expiresInMinutes: json['expires_in_minutes'] as int? ?? 5,
      deliveryStatus: json['delivery_status'] as String?,
      phoneMasked: json['phone_masked'] as String?,
      note: json['note'] as String?,
      message: json['message'] as String?,
    );
  }
}
