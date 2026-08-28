import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/models/otp_delivery_model.dart';
import 'package:smart_food_waste_donation/widgets/otp_delivery_status_widget.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:provider/provider.dart';

void main() {
  group('OtpDeliveryModel Unit Tests', () {
    test('OtpDeliveryInfo parses JSON correctly', () {
      final json = {
        'delivery_status': 'DELIVERED',
        'status_display': '✅ SMS delivered',
        'phone_masked': '+91 ****3210',
        'provider': 'mock',
        'sent_at': '2026-08-23T10:00:00Z',
        'delivered_at': '2026-08-23T10:00:05Z',
        'otp_available': true,
        'otp_record_id': 42,
        'remaining_seconds': 285,
      };

      final info = OtpDeliveryInfo.fromJson(json);

      expect(info.deliveryStatus, 'DELIVERED');
      expect(info.isDelivered, isTrue);
      expect(info.isFailed, isFalse);
      expect(info.isExpired, isFalse);
      expect(info.phoneMasked, '+91 ****3210');
      expect(info.otpRecordId, 42);
      expect(info.remainingFormatted, '04:45');
    });

    test('OtpDeliveryStatusDisplay maps each status correctly', () {
      final delivered = OtpDeliveryStatusDisplay.fromStatus('DELIVERED');
      expect(delivered.icon, '✅');
      expect(delivered.label, 'Delivered');

      final sent = OtpDeliveryStatusDisplay.fromStatus('SENT');
      expect(sent.icon, '✓');
      expect(sent.label, 'Sent');

      final failed = OtpDeliveryStatusDisplay.fromStatus('FAILED');
      expect(failed.icon, '⚠');
      expect(failed.label, 'Failed');

      final queued = OtpDeliveryStatusDisplay.fromStatus('QUEUED');
      expect(queued.icon, '📤');
      expect(queued.label, 'Sending');

      final expired = OtpDeliveryStatusDisplay.fromStatus('EXPIRED');
      expect(expired.icon, '⏰');
      expect(expired.label, 'Expired');
    });

    test('PickupOtpGenerateResult parses JSON correctly', () {
      final json = {
        'otp': '964907',
        'expires_at': '2026-08-23T10:05:00Z',
        'expires_in_minutes': 5,
        'delivery_status': 'SENT',
        'phone_masked': '+91 ****3210',
        'note': 'Delivery confirmation unavailable (mock)',
      };

      final result = PickupOtpGenerateResult.fromJson(json);

      expect(result.otp, '964907');
      expect(result.expiresInMinutes, 5);
      expect(result.deliveryStatus, 'SENT');
      expect(result.phoneMasked, '+91 ****3210');
      expect(result.note, contains('mock'));
    });
  });

  group('OtpDeliveryStatusWidget UI Widget Tests', () {
    Widget buildTestWidget(Widget child) {
      return ChangeNotifierProvider<LocaleProvider>(
        create: (_) => LocaleProvider(),
        child: MaterialApp(
          home: Scaffold(body: child),
        ),
      );
    }

    testWidgets('Renders DELIVERED status correctly', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(const OtpDeliveryStatusWidget(status: 'DELIVERED')),
      );
      await tester.pumpAndSettle();

      expect(find.text('✅'), findsOneWidget);
      expect(find.byType(OtpDeliveryStatusWidget), findsOneWidget);
    });

    testWidgets('Renders FAILED status with warning icon', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(const OtpDeliveryStatusWidget(status: 'FAILED')),
      );
      await tester.pumpAndSettle();

      expect(find.text('⚠'), findsOneWidget);
    });

    testWidgets('Compact badge renders inline without crashing', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(const OtpDeliveryStatusBadge(status: 'DELIVERED')),
      );
      await tester.pumpAndSettle();

      expect(find.text('✅'), findsOneWidget);
      expect(find.byType(OtpDeliveryStatusBadge), findsOneWidget);
    });
  });
}
