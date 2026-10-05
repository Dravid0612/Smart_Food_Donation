/// Notification Service — Smart Food Rescue (Flutter)
/// Handles FCM initialization, token registration, and deep-link routing.
///
/// SECURITY:
/// - Push notification payload NEVER contains OTP, JWT, full phone number.
/// - Deep-link data contains only safe routing keys: type + donation_id.
/// - OTP is fetched from the authenticated API after navigating to the correct screen.
library notification_service;

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../core/api/api_client.dart';

/// Top-level background message handler required by FirebaseMessaging.
/// Must be annotated with @pragma('vm:entry-point') so Flutter does not tree-shake it.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Already initialized or platform configuration deferred
  }
  debugPrint('[FCM Background] Message ID: ${message.messageId}, type: ${message.data['type']}');
}

/// Notification deep-link event types (mirrors backend)
class NotificationEventType {
  static const volunteerArrived = 'VOLUNTEER_ARRIVED';
  static const volunteerOnTheWay = 'VOLUNTEER_ON_THE_WAY';
  static const volunteerAssigned = 'VOLUNTEER_ASSIGNED';
  static const otpSmsSent = 'OTP_SMS_SENT';
  static const otpSmsDelivered = 'OTP_SMS_DELIVERED';
  static const otpSmsFailed = 'OTP_SMS_FAILED';
  static const pickupCompleted = 'PICKUP_COMPLETED';
  static const rescueCompleted = 'RESCUE_COMPLETED';
  static const rescueAtRisk = 'RESCUE_AT_RISK';
  static const feedbackReminder = 'FEEDBACK_REMINDER';
  static const donationCreated = 'DONATION_CREATED';
  static const donationAccepted = 'DONATION_ACCEPTED';
  static const distributionCompleted = 'DISTRIBUTION_COMPLETED';
  static const adminEscalation = 'ADMIN_ESCALATION';
}

/// Parses deep_link_data from a notification and routes to the correct screen.
void handleNotificationDeepLink(
  BuildContext context,
  Map<String, dynamic>? deepLinkData,
) {
  if (deepLinkData == null) return;

  final type = deepLinkData['type'] as String?;
  final donationIdStr = deepLinkData['donation_id'] as String?;
  final donationId = donationIdStr != null ? int.tryParse(donationIdStr) : null;

  switch (type) {
    case NotificationEventType.volunteerArrived:
    case NotificationEventType.otpSmsSent:
    case NotificationEventType.otpSmsDelivered:
    case NotificationEventType.otpSmsFailed:
      // Route to pickup OTP screen (donor only)
      if (donationId != null) {
        context.push('/donation/$donationId/pickup-otp');
      }
      break;

    case NotificationEventType.rescueCompleted:
    case NotificationEventType.feedbackReminder:
      // Route to feedback screen
      if (donationId != null) {
        context.push('/donation/$donationId?tab=feedback');
      }
      break;

    case NotificationEventType.volunteerOnTheWay:
    case NotificationEventType.volunteerAssigned:
    case NotificationEventType.pickupCompleted:
    case NotificationEventType.donationCreated:
    case NotificationEventType.donationAccepted:
    case NotificationEventType.distributionCompleted:
      // Route to donation detail
      if (donationId != null) {
        context.push('/donation/$donationId');
      }
      break;

    case NotificationEventType.rescueAtRisk:
    case NotificationEventType.adminEscalation:
      // Route to donation detail with urgency tab
      if (donationId != null) {
        context.push('/donation/$donationId?tab=urgency');
      }
      break;

    default:
      // Unknown event type — navigate to notifications list
      context.push('/notifications');
  }
}

/// Parses deep_link_data JSON string from notification
Map<String, dynamic>? parseDeepLinkData(String? deepLinkDataJson) {
  if (deepLinkDataJson == null || deepLinkDataJson.isEmpty) return null;
  try {
    return jsonDecode(deepLinkDataJson) as Map<String, dynamic>;
  } catch (_) {
    return null;
  }
}

class NotificationService {
  final ApiClient _apiClient;
  String? _lastRegisteredToken;
  bool _isInitialized = false;

  NotificationService([ApiClient? apiClient]) : _apiClient = apiClient ?? ApiClient();

  /// Whether Firebase messaging has been initialized.
  bool get isInitialized => _isInitialized;

  /// Initializes Firebase and configures FCM listeners.
  /// Safely handles situations where Firebase options / google-services.json are pending.
  Future<void> initializeFirebase({
    void Function(RemoteMessage message)? onForegroundMessage,
    void Function(Map<String, dynamic> data)? onNotificationTap,
  }) async {
    if (_isInitialized) return;
    try {
      await Firebase.initializeApp();

      // Register background message handler
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      // Request notification permissions (Android 13+ / iOS)
      await requestPermission();

      // Setup foreground message listener
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint('[FCM Foreground] Received: ${message.notification?.title}');
        if (onForegroundMessage != null) {
          onForegroundMessage(message);
        }
      });

      // Setup notification tap handler when app is in background
      FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
        debugPrint('[FCM Tap] App opened from background notification: ${message.data}');
        if (onNotificationTap != null) {
          onNotificationTap(message.data);
        }
      });

      // Check if app was opened from terminated state via notification tap
      final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
      if (initialMessage != null && onNotificationTap != null) {
        debugPrint('[FCM Initial] App opened from terminated state notification: ${initialMessage.data}');
        onNotificationTap(initialMessage.data);
      }

      // Listen for token refreshes and register updated token
      FirebaseMessaging.instance.onTokenRefresh.listen((String newToken) {
        debugPrint('[FCM] Device token refreshed');
        registerFcmToken(newToken);
      });

      // Get initial device token and register with backend
      final token = await getDeviceToken();
      if (token != null) {
        await registerFcmToken(token);
      }

      _isInitialized = true;
      debugPrint('[NotificationService] Firebase & FCM lifecycle initialized successfully');
    } catch (e) {
      debugPrint('[NotificationService] Firebase initialization deferred (manual configuration pending): $e');
    }
  }

  /// Requests notification permissions (Android 13+ / iOS).
  Future<NotificationSettings?> requestPermission() async {
    try {
      final settings = await FirebaseMessaging.instance.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );
      debugPrint('[NotificationService] Notification permission status: ${settings.authorizationStatus}');
      return settings;
    } catch (e) {
      debugPrint('[NotificationService] Could not request notification permission: $e');
      return null;
    }
  }

  /// Retrieves the current FCM registration token.
  Future<String?> getDeviceToken() async {
    try {
      final token = await FirebaseMessaging.instance.getToken();
      return token;
    } catch (e) {
      debugPrint('[NotificationService] Failed to get FCM device token: $e');
      return null;
    }
  }

  /// Registers an FCM device token with the backend.
  Future<void> registerFcmToken(String token) async {
    if (_lastRegisteredToken == token) {
      return; // Token already registered during this session, skip redundant call
    }
    try {
      await _apiClient.dio.post('/notifications/device-token', data: {
        'fcm_token': token,
      });
      _lastRegisteredToken = token;
      debugPrint('[NotificationService] FCM token registered with backend');
    } catch (e) {
      debugPrint('[NotificationService] FCM token registration failed: $e');
    }
  }

  /// Clears the FCM device token from the backend and local instance upon user logout.
  Future<void> unregisterFcmToken() async {
    try {
      await _apiClient.dio.delete('/notifications/device-token');
      _lastRegisteredToken = null;
      debugPrint('[NotificationService] FCM token removed from backend');
    } catch (e) {
      debugPrint('[NotificationService] FCM token unregistration failed: $e');
    }

    try {
      await FirebaseMessaging.instance.deleteToken();
      debugPrint('[NotificationService] Local FCM device token deleted');
    } catch (e) {
      debugPrint('[NotificationService] Local FCM token deletion skipped: $e');
    }
  }


  /// Fetches notification preferences for the current user.
  Future<Map<String, dynamic>?> getPreferences() async {
    try {
      final response = await _apiClient.dio.get('/notifications/preferences');
      if (response.statusCode == 200 && response.data != null) {
        return response.data as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[NotificationService] Failed to load preferences: $e');
    }
    return null;
  }

  /// Updates notification preferences.
  Future<bool> updatePreferences({
    bool? operationalNotifications,
    bool? urgentRescueAlerts,
    bool? impactUpdates,
    bool? feedbackReminders,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (operationalNotifications != null) body['operational_notifications'] = operationalNotifications;
      if (urgentRescueAlerts != null) body['urgent_rescue_alerts'] = urgentRescueAlerts;
      if (impactUpdates != null) body['impact_updates'] = impactUpdates;
      if (feedbackReminders != null) body['feedback_reminders'] = feedbackReminders;

      final response = await _apiClient.dio.put('/notifications/preferences', data: body);
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[NotificationService] Failed to update preferences: $e');
      return false;
    }
  }

  /// Marks a notification as opened (for lifecycle tracking).
  Future<void> markOpened(int notificationId) async {
    try {
      await _apiClient.dio.post('/notifications/$notificationId/opened');
    } catch (_) {
      // Non-critical
    }
  }

  /// Marks all notifications as read.
  Future<bool> markAllRead() async {
    try {
      final response = await _apiClient.dio.put('/notifications/read-all');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[NotificationService] Failed to mark all read: $e');
      return false;
    }
  }

  /// Gets unread notification count.
  Future<int> getUnreadCount() async {
    try {
      final response = await _apiClient.dio.get('/notifications/unread-count');
      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        return data['unread_count'] as int? ?? 0;
      }
    } catch (_) {}
    return 0;
  }
}
