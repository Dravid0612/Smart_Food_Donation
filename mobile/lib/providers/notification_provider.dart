import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/notification_model.dart';

class NotificationProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  List<NotificationModel> _notifications = [];
  bool _isLoading = false;
  String? _lastServerTime;
  int _unreadCount = 0;

  List<NotificationModel> get notifications => _notifications;
  bool get isLoading => _isLoading;
  int get unreadCount => _unreadCount > 0 ? _unreadCount : _notifications.where((n) => !n.isRead).length;

  Future<void> fetchNotifications() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/notifications/feed');
      if (response.data is Map<String, dynamic>) {
        final list = response.data['notifications'] as List? ?? [];
        _notifications = list.map((json) => NotificationModel.fromJson(json as Map<String, dynamic>)).toList();
        _lastServerTime = response.data['server_time'] as String?;
        _unreadCount = response.data['unread_count'] as int? ?? _notifications.where((n) => !n.isRead).length;
      } else if (response.data is List) {
        _notifications = (response.data as List).map((json) => NotificationModel.fromJson(json)).toList();
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchDelta() async {
    try {
      final queryParams = _lastServerTime != null ? {'since': _lastServerTime} : <String, dynamic>{};
      final response = await _apiClient.dio.get('/notifications/feed', queryParameters: queryParams);
      if (response.data is Map<String, dynamic>) {
        final list = response.data['notifications'] as List? ?? [];
        final newItems = list.map((json) => NotificationModel.fromJson(json as Map<String, dynamic>)).toList();
        if (newItems.isNotEmpty) {
          final existingIds = _notifications.map((n) => n.id).toSet();
          final uniqueNew = newItems.where((n) => !existingIds.contains(n.id)).toList();
          _notifications = [...uniqueNew, ..._notifications];
        }
        _lastServerTime = response.data['server_time'] as String? ?? _lastServerTime;
        _unreadCount = response.data['unread_count'] as int? ?? _unreadCount;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> markAsRead(int notificationId) async {
    try {
      await _apiClient.dio.put('/notifications/$notificationId/read');
      await fetchNotifications();
    } catch (_) {}
  }

  Future<void> markAllAsRead() async {
    try {
      await _apiClient.dio.put('/notifications/read-all');
      await fetchNotifications();
    } catch (_) {}
  }
}
