import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';

void main() {
  setUp(() {
    AppLocale.setLocale('en');
  });

  group('AppLocale', () {
    test('defaults to english code', () {
      expect(AppLocale.code.value, 'en');
    });

    test('switches language with setLocale', () {
      AppLocale.setLocale('ta');
      expect(AppLocale.code.value, 'ta');

      AppLocale.setLocale('hi');
      expect(AppLocale.code.value, 'hi');

      // Invalid locale does not change code
      AppLocale.setLocale('xyz');
      expect(AppLocale.code.value, 'hi');
    });

    test('translates english strings correctly', () {
      AppLocale.setLocale('en');
      expect(AppLocale.t('app_name'), 'Smart Donor');
      expect(AppLocale.t('tagline'), 'Rescue surplus food before it goes to waste');
      expect(AppLocale.t('invalid_credentials'), 'Invalid credentials.');
      expect(AppLocale.t('log_in'), 'Log in');
      expect(AppLocale.t('create_account'), 'Create account');
      expect(AppLocale.t('role_donor'), 'Donor');
      expect(AppLocale.t('role_ngo'), 'NGO');
      expect(AppLocale.t('role_volunteer'), 'Volunteer');
      expect(AppLocale.t('vehicle_bike'), 'Bike');
      expect(AppLocale.t('verification_pending'), 'Verification pending');
      expect(AppLocale.t('check_status'), 'Check status');
      expect(AppLocale.t('log_out'), 'Log out');
    });

    test('translates tamil strings correctly', () {
      AppLocale.setLocale('ta');
      expect(AppLocale.t('app_name'), 'Smart Donor');
      expect(AppLocale.t('tagline'), 'உபரி உணவு வீணாகும் முன் அதைக் காப்பாற்றுங்கள்');
      expect(AppLocale.t('invalid_credentials'), 'தவறான உள்நுழைவு விவரங்கள்.');
      expect(AppLocale.t('log_in'), 'உள்நுழையவும்');
      expect(AppLocale.t('role_donor'), 'நன்கொடையாளர்');
      expect(AppLocale.t('role_ngo'), 'NGO');
      expect(AppLocale.t('role_volunteer'), 'தன்னார்வலர்');
      expect(AppLocale.t('vehicle_bike'), 'பைக்');
      expect(AppLocale.t('verification_pending'), 'சரிபார்ப்பு நிலுவையில் உள்ளது');
      expect(AppLocale.t('check_status'), 'நிலையைச் சரிபார்க்கவும்');
      expect(AppLocale.t('log_out'), 'வெளியேறு');
    });

    test('translates hindi strings correctly', () {
      AppLocale.setLocale('hi');
      expect(AppLocale.t('app_name'), 'Smart Donor');
      expect(AppLocale.t('tagline'), 'अतिरिक्त भोजन बर्बाद होने से पहले उसे बचाएं');
      expect(AppLocale.t('invalid_credentials'), 'अमान्य लॉगिन जानकारी।');
      expect(AppLocale.t('log_in'), 'लॉग इन करें');
      expect(AppLocale.t('role_donor'), 'दानकर्ता');
      expect(AppLocale.t('role_ngo'), 'NGO');
      expect(AppLocale.t('role_volunteer'), 'स्वयंसेवक');
      expect(AppLocale.t('vehicle_bike'), 'बाइक');
      expect(AppLocale.t('verification_pending'), 'सत्यापन लंबित है');
      expect(AppLocale.t('check_status'), 'स्थिति जांचें');
      expect(AppLocale.t('log_out'), 'लॉग आउट करें');
    });

    test('falls back to key if translation not found', () {
      AppLocale.setLocale('en');
      expect(AppLocale.t('non_existent_key_123'), 'non_existent_key_123');
    });

    test('ValueNotifier notifies listeners on change', () {
      String? updated;
      void listener() {
        updated = AppLocale.code.value;
      }

      AppLocale.code.addListener(listener);
      AppLocale.setLocale('ta');
      expect(updated, 'ta');
      AppLocale.code.removeListener(listener);
    });
  });
}
