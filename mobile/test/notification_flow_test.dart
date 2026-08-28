import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/models/notification_model.dart';
import 'package:smart_food_waste_donation/services/notification_service.dart';

void main() {
  group('Notification Model & Deep Link Tests', () {
    test('NotificationModel parses event_type and deep_link_data correctly', () {
      final json = {
        'id': 101,
        'user_id': 1,
        'title': 'Volunteer Has Arrived 📍',
        'message': 'Your volunteer has arrived. Open app to view secure code.',
        'type': 'assignment',
        'related_donation_id': 86,
        'is_read': false,
        'created_at': '2026-08-23T10:00:00Z',
        'event_type': 'VOLUNTEER_ARRIVED',
        'deep_link_data': '{"type": "VOLUNTEER_ARRIVED", "donation_id": "86"}',
        'is_sent': true,
      };

      final model = NotificationModel.fromJson(json);

      expect(model.id, 101);
      expect(model.eventType, 'VOLUNTEER_ARRIVED');
      expect(model.isSent, isTrue);
      expect(model.deepLinkMap, isNotNull);
      expect(model.deepLinkMap!['type'], 'VOLUNTEER_ARRIVED');
      expect(model.deepLinkMap!['donation_id'], '86');
    });

    test('parseDeepLinkData returns null for empty or invalid json', () {
      expect(parseDeepLinkData(null), isNull);
      expect(parseDeepLinkData(''), isNull);
      expect(parseDeepLinkData('{not valid json}'), isNull);
    });

    test('parseDeepLinkData parses valid JSON payload correctly', () {
      final parsed = parseDeepLinkData('{"type": "RESCUE_COMPLETED", "donation_id": "42"}');
      expect(parsed, isNotNull);
      expect(parsed!['type'], 'RESCUE_COMPLETED');
      expect(parsed['donation_id'], '42');
    });

    test('deep_link payload never contains sensitive keys', () {
      final payload = parseDeepLinkData('{"type": "VOLUNTEER_ARRIVED", "donation_id": "86"}');
      expect(payload!.containsKey('otp'), isFalse);
      expect(payload.containsKey('password'), isFalse);
      expect(payload.containsKey('token'), isFalse);
      expect(payload.containsKey('phone'), isFalse);
    });
  });
}
