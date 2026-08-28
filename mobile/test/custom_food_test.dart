import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';

void main() {
  group('Custom Food & Flexible Donation Flutter Tests', () {
    test('Trilingual custom food keys exist across EN, TA, and HI', () {
      final translations = LocaleProvider.translations;
      final requiredKeys = [
        'custom_food',
        'add_custom_food',
        'my_foods_library',
        'select_from_library',
        'custom_food_name',
        'food_description',
        'major_ingredients',
        'broad_category_hint',
        'flexible_quantity',
        'quantity_unit_label',
        'estimated_meals_count',
        'rule_coverage_label',
        'rule_coverage_high',
        'rule_coverage_medium',
        'rule_coverage_low',
        'custom_food_advisory_note',
        'unit_meals',
        'unit_portions',
        'unit_kg',
        'unit_grams',
        'unit_litres',
        'unit_ml',
        'unit_pieces',
        'unit_packets',
        'unit_boxes',
        'unit_trays',
        'unit_containers',
        'unit_plates',
        'unit_bottles',
        'unit_custom',
      ];

      for (final lang in ['en', 'ta', 'hi']) {
        final langDict = translations[lang];
        expect(langDict, isNotNull, reason: 'Language $lang dictionary should exist');
        for (final key in requiredKeys) {
          expect(
            langDict!.containsKey(key),
            isTrue,
            reason: 'Key "$key" must exist in language "$lang"',
          );
          expect(
            langDict[key]!.isNotEmpty,
            isTrue,
            reason: 'Key "$key" in "$lang" must not be empty',
          );
        }
      }
    });

    test('DonorCustomFoodProfileModel JSON parsing and construction', () {
      final json = {
        'id': 101,
        'donor_id': 5,
        'name': 'Vegetable Pongal',
        'food_category': 'cooked_rice_grain',
        'description': 'Traditional rice and yellow lentil dish with mild pepper and cashews',
        'major_ingredients': 'rice, moong dal, pepper, cashews, ghee',
        'common_storage': 'Room Temperature',
        'default_unit': 'Containers',
        'usage_count': 3,
        'created_at': '2026-08-20T10:00:00Z',
      };

      final profile = DonorCustomFoodProfileModel.fromJson(json);
      expect(profile.id, 101);
      expect(profile.donorId, 5);
      expect(profile.name, 'Vegetable Pongal');
      expect(profile.foodCategory, 'cooked_rice_grain');
      expect(profile.defaultUnit, 'Containers');
      expect(profile.usageCount, 3);
    });

    test('DonationModel custom food fields parsing', () {
      final json = {
        'id': 42,
        'donor_id': 5,
        'food_name': 'Vegetable Pongal',
        'food_source': 'CUSTOM',
        'custom_food_name': 'Vegetable Pongal',
        'food_description': 'Traditional dish',
        'major_ingredients': 'rice, moong dal',
        'food_category': 'cooked_rice_grain',
        'quantity': 5.0,
        'quantity_unit': 'Containers',
        'quantity_unit_label': 'Hot Packs',
        'estimated_meals': 25.0,
        'rule_coverage': 'MEDIUM',
        'preparation_time': '2026-08-20T08:00:00Z',
        'expiry_time': '2026-08-20T14:00:00Z',
        'pickup_address': 'MG Road, Bengaluru',
        'status': 'pending',
        'created_at': '2026-08-20T08:15:00Z',
        'rescue_window': {
          'food_type': 'Vegetable Pongal',
          'food_category': 'cooked_rice_grain',
          'rule_source': 'Generic Category Rules',
          'rule_version': '2026.1',
          'rule_coverage': 'MEDIUM',
          'is_custom': true,
          'visual_condition': 'GOOD',
          'estimated_window_start': '2026-08-20T08:00:00Z',
          'estimated_window_end': '2026-08-20T12:00:00Z',
          'remaining_minutes': 180,
          'estimated_window_display': '~3.0 hours',
          'urgency_level': 'APPROACHING',
          'urgency_score': 0.45,
          'confidence': 0.88,
          'reasons': ['Custom food evaluated under cooked_rice_grain generic parameters'],
        }
      };

      final donation = DonationModel.fromJson(json);
      expect(donation.foodSource, 'CUSTOM');
      expect(donation.customFoodName, 'Vegetable Pongal');
      expect(donation.quantity, 5.0);
      expect(donation.quantityUnit, 'Containers');
      expect(donation.quantityUnitLabel, 'Hot Packs');
      expect(donation.estimatedMeals, 25.0);
      expect(donation.ruleCoverage, 'MEDIUM');
      expect(donation.rescueWindow, isNotNull);
      expect(donation.rescueWindow!.ruleCoverage, 'MEDIUM');
      expect(donation.rescueWindow!.isCustom, isTrue);
    });
  });
}
