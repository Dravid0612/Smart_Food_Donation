import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Secure OTP Delivery & Handover UX Tests', () {
    test('Trilingual OTP Handover strings parity across en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.translate('pickup_verification'), equals('Pickup Verification'));
      expect(provider.translate('show_code_to_volunteer'), equals('Show this code to your volunteer'));
      expect(provider.translate('show_pickup_code'), equals('Show Pickup Code'));
      expect(provider.translate('show_to_volunteer'), equals('Show to Volunteer'));
      expect(provider.translate('request_new_code'), equals('Request New Code'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.translate('pickup_verification'), equals('பிக்அப் சரிபார்ப்பு'));
      expect(provider.translate('show_code_to_volunteer'), equals('இந்தக் குறியீட்டை உங்கள் தன்னார்வலரிடம் காட்டுங்கள்'));
      expect(provider.translate('show_pickup_code'), equals('பிக்அப் குறியீட்டைக் காட்டு'));
      expect(provider.translate('show_to_volunteer'), equals('தன்னார்வலரிடம் காட்டு'));
      expect(provider.translate('request_new_code'), equals('புதிய குறியீட்டைக் கோருங்கள்'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.translate('pickup_verification'), equals('पिकअप सत्यापन'));
      expect(provider.translate('show_code_to_volunteer'), equals('यह कोड अपने स्वयंसेवक को दिखाएं'));
      expect(provider.translate('show_pickup_code'), equals('पिकअप कोड दिखाएं'));
      expect(provider.translate('show_to_volunteer'), equals('स्वयंसेवक को दिखाएं'));
      expect(provider.translate('request_new_code'), equals('नया कोड प्राप्त करें'));
    });

    test('Zero plaintext OTP exposure in push notification copy', () async {
      final provider = LocaleProvider();

      for (final lang in ['en', 'ta', 'hi']) {
        await provider.setLanguage(lang);
        final arrivedTitle = provider.translate('volunteer_arrived_title');
        final arrivedDesc = provider.translate('volunteer_arrived_desc');
        final onTheWayTitle = provider.translate('volunteer_on_the_way_title');
        final onTheWayDesc = provider.translate('volunteer_on_the_way_desc');

        // Verify no 6-digit pin appears in notification templates
        for (final text in [arrivedTitle, arrivedDesc, onTheWayTitle, onTheWayDesc]) {
          final words = text.split(' ');
          for (final w in words) {
            expect(w.length == 6 && int.tryParse(w) != null, isFalse,
                reason: 'Language $lang notification text "$text" must not contain 6-digit OTP');
          }
        }
      }
    });

    test('Progressive disclosure stages cover arrival and handover correctly', () async {
      final provider = LocaleProvider();
      await provider.setLanguage('en');

      expect(provider.translate('volunteer_on_the_way_title'), contains('on the way'));
      expect(provider.translate('volunteer_arrived_title'), contains('arrived'));
      expect(provider.translate('code_expires_in', {'time': '04:32'}), equals('Code expires in 04:32'));
      expect(provider.translate('semantic_otp_code', {'digits': '5 8 3 2 1 4'}), equals('Pickup verification code: 5 8 3 2 1 4'));
    });
  });
}
