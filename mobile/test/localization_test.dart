import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Trilingual Localization Core Tests', () {
    test('LocaleProvider initializes with default locale (en)', () async {
      final provider = LocaleProvider();
      expect(provider.currentLanguage, equals('en'));
      expect(provider.locale.languageCode, equals('en'));
    });

    test('LocaleProvider switches language to Tamil (ta) and persists', () async {
      final provider = LocaleProvider();
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.locale.languageCode, equals('ta'));

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('selected_language'), equals('ta'));
    });

    test('LocaleProvider switches language to Hindi (hi) and persists', () async {
      final provider = LocaleProvider();
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.locale.languageCode, equals('hi'));

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('selected_language'), equals('hi'));
    });

    test('Translation dictionary contains complete translations for all keys across en, ta, and hi', () {
      final enKeys = LocaleProvider.translations['en']!.keys.toSet();
      final taKeys = LocaleProvider.translations['ta']!.keys.toSet();
      final hiKeys = LocaleProvider.translations['hi']!.keys.toSet();

      // Check key parity
      final missingInTamil = enKeys.difference(taKeys);
      final missingInHindi = enKeys.difference(hiKeys);

      expect(missingInTamil, isEmpty, reason: 'Tamil is missing keys: $missingInTamil');
      expect(missingInHindi, isEmpty, reason: 'Hindi is missing keys: $missingInHindi');
    });

    test('Domain helper translations for Categories in en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getFoodCategory('cooked_food'), equals('Cooked Food'));
      expect(provider.getFoodCategory('bakery'), equals('Bakery & Bread'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getFoodCategory('bakery'), equals('ரொட்டி & பேக்கரி'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getFoodCategory('bakery'), equals('बेकरी और ब्रेड'));
    });

    test('Domain helper translations for Food Items in en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getFoodItem('Rice'), equals('Rice'));
      expect(provider.getFoodItem('Biryani'), equals('Biryani'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getFoodItem('Biryani'), equals('பிரியாணி'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getFoodItem('Biryani'), equals('बिरयानी'));
    });

    test('Domain helper translations for Storage Methods in en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getStorageMethod('room_temperature'), equals('Room Temperature'));
      expect(provider.getStorageMethod('refrigerated'), equals('Refrigerated'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getStorageMethod('refrigerated'), equals('குளிர்சாதனப் பெட்டி'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getStorageMethod('refrigerated'), equals('रेफ्रिजरेटर में रखा'));
    });

    test('Domain helper translations for Urgency Levels in en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getUrgency('Fresh'), equals('Fresh'));
      expect(provider.getUrgency('Urgent'), equals('Urgent'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getUrgency('Urgent'), equals('அவசரம்'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getUrgency('Urgent'), equals('अत्यावश्यक'));
    });

    test('Domain helper translations for Statuses in en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getStatus('pending'), equals('Pending NGO Match'));
      expect(provider.getStatus('collected'), equals('Collected (In Transit)'));
      expect(provider.getStatus('delivered'), equals('Delivered to NGO'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getStatus('collected'), equals('பெறப்பட்டது (பயணத்தில் உள்ளது)'));
      expect(provider.getStatus('delivered'), equals('NGO-விடம் ஒப்படைக்கப்பட்டது'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getStatus('collected'), equals('प्राप्त किया (मार्ग में)'));
      expect(provider.getStatus('delivered'), equals('एनजीओ को डिलीवर किया'));
    });

    test('Safety Disclaimer translations match requirements in all 3 languages', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getSafetyDisclaimer(), equals('Visual assessment only. AI visual assessment does not certify food safety.'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
    });

    test('Dynamic parameter interpolations preserve raw digits', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.getRemainingMinutesText(45), equals('45 minutes remaining'));
      expect(provider.getMealsCountText(150), equals('150 meals'));
      expect(provider.getOtpInstructionDonor('482910'), contains('482910'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.getSafetyDisclaimer(), equals('காட்சி மதிப்பீடு மட்டுமே. AI காட்சி மதிப்பீடு உணவுப் பாதுகாப்பைச் சான்றளிக்காது.'));
      expect(provider.getMealsCountText(150), equals('150 உணவுகள்'));
      expect(provider.getOtpInstructionDonor('482910'), contains('482910'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.getSafetyDisclaimer(), equals('केवल दृश्य मूल्यांकन। एआई दृश्य मूल्यांकन खाद्य सुरक्षा प्रमाणित नहीं करता है।'));
      expect(provider.getMealsCountText(150), equals('150 भोजन'));
      expect(provider.getOtpInstructionDonor('482910'), contains('482910'));
    });
  });
}
