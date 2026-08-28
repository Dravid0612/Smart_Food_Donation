import 'dart:convert';

class NotificationModel {
  final int id;
  final int userId;
  final String title;
  final String message;
  final String type;
  final int? relatedDonationId;
  final bool isRead;
  final String createdAt;
  final String? eventType;
  final String? deepLinkData;
  final bool isSent;
  final String? sentAt;
  final String? openedAt;

  NotificationModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.message,
    required this.type,
    this.relatedDonationId,
    required this.isRead,
    required this.createdAt,
    this.eventType,
    this.deepLinkData,
    this.isSent = false,
    this.sentAt,
    this.openedAt,
  });

  Map<String, dynamic>? get deepLinkMap {
    if (deepLinkData == null || deepLinkData!.isEmpty) return null;
    try {
      return jsonDecode(deepLinkData!) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    return NotificationModel(
      id: json['id'],
      userId: json['user_id'],
      title: json['title'] ?? '',
      message: json['message'] ?? '',
      type: json['type'] ?? 'info',
      relatedDonationId: json['related_donation_id'],
      isRead: json['is_read'] ?? false,
      createdAt: json['created_at'] ?? '',
      eventType: json['event_type'],
      deepLinkData: json['deep_link_data'],
      isSent: json['is_sent'] ?? false,
      sentAt: json['sent_at'],
      openedAt: json['opened_at'],
    );
  }
}

