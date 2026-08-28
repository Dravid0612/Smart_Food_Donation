import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Proactive Time-Critical Rescue Alerts - Localization & Text Tests', () {
    test('English translations for proactive alert reassurance are present and non-empty', () {
      final provider = LocaleProvider();
      expect(provider.translate('proactive_reassurance_urgent'), contains('prioritizing nearby feasible rescue partners'));
      expect(provider.translate('proactive_reassurance_critical'), contains('Critical'));
      expect(provider.translate('proactive_outreach_active'), contains('Active Rescue Partner Outreach'));
      expect(provider.translate('proactive_tab_urgent'), equals('Urgent Rescues'));
      expect(provider.translate('proactive_tab_critical'), equals('Critical Rescues'));
    });

    test('Tamil translations for proactive alerts are natural and complete', () async {
      final provider = LocaleProvider();
      await provider.setLanguage('ta');
      expect(provider.translate('proactive_outreach_active'), contains('மீட்பு அமைப்புகள் தொடர்பு கொள்ளப்படுகின்றன'));
      expect(provider.translate('proactive_reassurance_urgent'), contains('முன்னுரிமை அளிக்கப்படுகிறது'));
      expect(provider.translate('proactive_tab_urgent'), contains('அவசர மீட்புகள்'));
      expect(provider.translate('proactive_tab_critical'), contains('மிக அவசர மீட்புகள்'));
    });

    test('Hindi translations for proactive alerts are accurate and clear', () async {
      final provider = LocaleProvider();
      await provider.setLanguage('hi');
      expect(provider.translate('proactive_outreach_active'), contains('सक्रिय बचाव भागीदार संपर्क'));
      expect(provider.translate('proactive_reassurance_urgent'), contains('प्राथमिकता दे रहे हैं'));
      expect(provider.translate('proactive_tab_urgent'), contains('तत्काल बचाव'));
      expect(provider.translate('proactive_tab_critical'), contains('अति गंभीर बचाव'));
    });
  });

  group('Proactive Rescue Model & Filtering Tests', () {
    test('urgent and critical criteria correctly filter pending donations', () {
      final now = DateTime.now().toUtc();
      final fresh = DonationModel(
        id: 1,
        donorId: 10,
        foodName: 'Fresh Rice',
        foodCategory: 'Cooked Food',
        quantity: 50.0,
        quantityUnit: 'Meals',
        preparationTime: now.subtract(const Duration(minutes: 15)).toIso8601String(),
        expiryTime: now.add(const Duration(hours: 4)).toIso8601String(),
        pickupAddress: 'Indiranagar, Bangalore',
        latitude: 12.9716,
        longitude: 77.5946,
        status: 'pending',
        urgencyLevel: 'Fresh',
        rescueUrgencyLevel: 'FRESH',
        remainingMinutes: 225,
        createdAt: now.toIso8601String(),
      );

      final urgent = DonationModel(
        id: 2,
        donorId: 10,
        foodName: 'Urgent Biryani',
        foodCategory: 'Cooked Food',
        quantity: 40.0,
        quantityUnit: 'Meals',
        preparationTime: now.subtract(const Duration(hours: 2, minutes: 30)).toIso8601String(),
        expiryTime: now.add(const Duration(minutes: 90)).toIso8601String(),
        pickupAddress: 'Koramangala, Bangalore',
        latitude: 12.9716,
        longitude: 77.5946,
        status: 'pending',
        urgencyLevel: 'Urgent',
        rescueUrgencyLevel: 'URGENT',
        remainingMinutes: 90,
        createdAt: now.toIso8601String(),
      );

      final critical = DonationModel(
        id: 3,
        donorId: 10,
        foodName: 'Critical Curry',
        foodCategory: 'Cooked Food',
        quantity: 30.0,
        quantityUnit: 'Meals',
        preparationTime: now.subtract(const Duration(hours: 3, minutes: 30)).toIso8601String(),
        expiryTime: now.add(const Duration(minutes: 30)).toIso8601String(),
        pickupAddress: 'MG Road, Bangalore',
        latitude: 12.9716,
        longitude: 77.5946,
        status: 'pending',
        urgencyLevel: 'Critical',
        rescueUrgencyLevel: 'CRITICAL',
        remainingMinutes: 30,
        createdAt: now.toIso8601String(),
      );

      final completedUrgent = DonationModel(
        id: 4,
        donorId: 10,
        foodName: 'Delivered Food',
        foodCategory: 'Cooked Food',
        quantity: 30.0,
        quantityUnit: 'Meals',
        preparationTime: now.subtract(const Duration(hours: 4)).toIso8601String(),
        expiryTime: now.add(const Duration(minutes: 30)).toIso8601String(),
        pickupAddress: 'Jayanagar, Bangalore',
        latitude: 12.9716,
        longitude: 77.5946,
        status: 'delivered', // Not pending!
        urgencyLevel: 'Critical',
        rescueUrgencyLevel: 'CRITICAL',
        remainingMinutes: 30,
        createdAt: now.toIso8601String(),
      );

      // Verify urgent filter
      final list = [fresh, urgent, critical, completedUrgent];
      final urgentList = list.where((d) {
        if (d.status.toLowerCase() != 'pending') return false;
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'URGENT';
      }).toList();

      expect(urgentList.length, equals(1));
      expect(urgentList.first.foodName, equals('Urgent Biryani'));

      // Verify critical filter
      final criticalList = list.where((d) {
        if (d.status.toLowerCase() != 'pending') return false;
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'CRITICAL';
      }).toList();

      expect(criticalList.length, equals(1));
      expect(criticalList.first.foodName, equals('Critical Curry'));
    });
  });
}
