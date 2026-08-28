import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Final Production Polish & Localization Parity Tests', () {
    test('Notification center keys exist in EN, TA, and HI', () async {
      final provider = LocaleProvider();
      const keys = [
        'notifications',
        'mark_all_read',
        'no_notifications',
        'no_notifications_desc',
      ];

      for (final lang in ['en', 'ta', 'hi']) {
        await provider.setLanguage(lang);
        for (final key in keys) {
          final val = provider.translate(key);
          expect(val, isNotEmpty, reason: '$lang missing key $key');
          expect(val, isNot(equals(key)), reason: '$lang returned raw key $key');
        }
      }
    });

    test('Draft discard dialog keys exist in EN, TA, and HI', () async {
      final provider = LocaleProvider();
      const keys = [
        'discard_draft_title',
        'discard_draft_desc',
        'keep_editing',
        'discard',
      ];

      for (final lang in ['en', 'ta', 'hi']) {
        await provider.setLanguage(lang);
        for (final key in keys) {
          final val = provider.translate(key);
          expect(val, isNotEmpty, reason: '$lang missing key $key');
          expect(val, isNot(equals(key)), reason: '$lang returned raw key $key');
        }
      }
    });

    test('Camera and Location permission context keys exist in EN, TA, and HI', () async {
      final provider = LocaleProvider();
      const keys = [
        'camera_permission_title',
        'camera_permission_desc',
        'location_permission_desc',
      ];

      for (final lang in ['en', 'ta', 'hi']) {
        await provider.setLanguage(lang);
        for (final key in keys) {
          final val = provider.translate(key);
          expect(val, isNotEmpty, reason: '$lang missing key $key');
          expect(val, isNot(equals(key)), reason: '$lang returned raw key $key');
        }
      }
    });

    test('Validation, Error categorization, and AI Disclaimer keys exist in EN, TA, and HI', () async {
      final provider = LocaleProvider();
      const keys = [
        'err_qty_zero',
        'err_prep_future',
        'err_address_empty',
        'err_user_input',
        'err_server_busy',
        'err_conflict_accepted',
        'ai_disclaimer_notice',
      ];

      for (final lang in ['en', 'ta', 'hi']) {
        await provider.setLanguage(lang);
        for (final key in keys) {
          final val = provider.translate(key);
          expect(val, isNotEmpty, reason: '$lang missing key $key');
          expect(val, isNot(equals(key)), reason: '$lang returned raw key $key');
        }
      }
    });
  });
}
