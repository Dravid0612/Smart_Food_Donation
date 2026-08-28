import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/admin_operations_model.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Admin Food Rescue Operations Control Center Tests', () {
    test('Trilingual Control Center strings parity across en, ta, and hi', () async {
      final provider = LocaleProvider();

      // English
      await provider.setLanguage('en');
      expect(provider.translate('food_rescue_operations'), equals('Food Rescue Operations'));
      expect(provider.translate('todays_overview'), equals('Today\'s Rescue Overview'));
      expect(provider.translate('active_rescues'), equals('Active Rescues'));
      expect(provider.translate('urgent_rescues'), equals('Urgent Rescues'));
      expect(provider.translate('in_transit'), equals('In Transit'));
      expect(provider.translate('food_received_today'), equals('Food Received'));
      expect(provider.translate('food_distributed_today'), equals('Food Distributed'));
      expect(provider.translate('critical_rescues'), equals('Critical Rescues'));
      expect(provider.translate('food_receiving'), equals('Food Receiving'));
      expect(provider.translate('quantity_mismatch'), equals('Quantity Mismatch'));
      expect(provider.translate('admin_intervene'), equals('Intervene'));
      expect(provider.translate('linear_food_flow'), equals('Food Flow Tracker'));

      // Tamil
      await provider.setLanguage('ta');
      expect(provider.translate('food_rescue_operations'), equals('உணவு மீட்பு செயல்பாடுகள்'));
      expect(provider.translate('todays_overview'), equals('இன்றைய மீட்பு கண்ணோட்டம்'));
      expect(provider.translate('active_rescues'), equals('செயலில் உள்ள மீட்புகள்'));
      expect(provider.translate('urgent_rescues'), equals('அவசர மீட்புகள்'));
      expect(provider.translate('in_transit'), equals('பயணத்தில் உள்ளது'));
      expect(provider.translate('food_received_today'), equals('பெறப்பட்ட உணவு'));
      expect(provider.translate('food_distributed_today'), equals('விநியோகிக்கப்பட்ட உணவு'));
      expect(provider.translate('critical_rescues'), equals('முக்கியமான மீட்புகள்'));
      expect(provider.translate('food_receiving'), equals('உணவு பெறுதல்'));
      expect(provider.translate('quantity_mismatch'), equals('அளவு பொருந்தவில்லை'));
      expect(provider.translate('admin_intervene'), equals('தலையிடு'));
      expect(provider.translate('linear_food_flow'), equals('உணவு ஓட்ட கண்காணிப்பாளர்'));

      // Hindi
      await provider.setLanguage('hi');
      expect(provider.translate('food_rescue_operations'), equals('भोजन बचाव संचालन'));
      expect(provider.translate('todays_overview'), equals('आज का बचाव अवलोकन'));
      expect(provider.translate('active_rescues'), equals('सक्रिय बचाव'));
      expect(provider.translate('urgent_rescues'), equals('अति आवश्यक बचाव'));
      expect(provider.translate('in_transit'), equals('पारगमन में'));
      expect(provider.translate('food_received_today'), equals('प्राप्त भोजन'));
      expect(provider.translate('food_distributed_today'), equals('वितरित भोजन'));
      expect(provider.translate('critical_rescues'), equals('गंभीर बचाव'));
      expect(provider.translate('food_receiving'), equals('भोजन प्राप्ति'));
      expect(provider.translate('quantity_mismatch'), equals('मात्रा बेमेल'));
      expect(provider.translate('admin_intervene'), equals('हस्तक्षेप करें'));
      expect(provider.translate('linear_food_flow'), equals('खाद्य प्रवाह ट्रैकर'));
    });

    test('AdminReceivingSummaryModel JSON parsing and metrics calculation', () {
      final json = {
        'active_rescues': 18,
        'urgent_rescues': 4,
        'critical_rescues': 2,
        'in_transit': 7,
        'received_today': 240.0,
        'distributed_today': 190.0,
        'remaining_today': 50.0,
        'issues_open': 3,
        'food_at_risk_meals': 120.0,
        'completed_today': 14,
      };

      final summary = AdminReceivingSummaryModel.fromJson(json);
      expect(summary.activeRescues, equals(18));
      expect(summary.urgentRescues, equals(4));
      expect(summary.criticalRescues, equals(2));
      expect(summary.inTransit, equals(7));
      expect(summary.receivedToday, equals(240.0));
      expect(summary.distributedToday, equals(190.0));
      expect(summary.remainingToday, equals(50.0));
      expect(summary.issuesOpen, equals(3));
      expect(summary.foodAtRiskMeals, equals(120.0));
      expect(summary.completedToday, equals(14));
    });

    test('AdminReceivingItemModel discrepancy and quantity mismatch parsing', () {
      final json = {
        'id': 86,
        'food_name': 'Vegetable Biryani',
        'food_category': 'Cooked Food',
        'quantity': 100.0,
        'quantity_unit': 'Meals',
        'donor_id': 5,
        'donor_name': 'Hotel Grand',
        'assigned_ngo_id': 2,
        'ngo_name': 'Green Hope Foundation',
        'assigned_volunteer_id': 8,
        'volunteer_name': 'Arun Kumar',
        'status': 'delivered',
        'rescue_urgency_level': 'URGENT',
        'remaining_minutes': 24,
        'ai_visual_condition': 'GOOD',
        'storage_method': 'Heated/Insulated',
        'packaging_condition': 'Sealed / Covered',
        'expected_quantity': 100.0,
        'received_quantity': 98.0,
        'has_quantity_mismatch': true,
        'discrepancy_amount': 2.0,
        'discrepancy_reason': 'Packaging damage during transport',
        'distributed_quantity': 60.0,
        'remaining_quantity': 38.0,
        'issue_count': 1,
        'pickup_address': '45 MG Road, Bangalore',
        'created_at': '2026-08-23T10:00:00Z',
      };

      final item = AdminReceivingItemModel.fromJson(json);
      expect(item.id, equals(86));
      expect(item.foodName, equals('Vegetable Biryani'));
      expect(item.expectedQuantity, equals(100.0));
      expect(item.receivedQuantity, equals(98.0));
      expect(item.hasQuantityMismatch, isTrue);
      expect(item.discrepancyAmount, equals(2.0));
      expect(item.discrepancyReason, equals('Packaging damage during transport'));
      expect(item.distributedQuantity, equals(60.0));
      expect(item.remainingQuantity, equals(38.0));
    });

    test('AdminRescueDetailModel 9-stage linear flow parsing', () {
      final json = {
        'id': 92,
        'food_name': 'Basmati Rice & Dal',
        'food_category': 'Cooked Food',
        'quantity': 50.0,
        'quantity_unit': 'Meals',
        'donor_id': 5,
        'status': 'collected',
        'rescue_urgency_level': 'CRITICAL',
        'remaining_minutes': 15,
        'expected_quantity': 50.0,
        'pickup_address': '12 Palace Road',
        'created_at': '2026-08-23T11:00:00Z',
        'timeline': [
          {'stage': 'DONATION_CREATED', 'label': 'Donation Created', 'is_completed': true, 'is_current': false},
          {'stage': 'AI_ANALYZED', 'label': 'AI Assessment', 'is_completed': true, 'is_current': false},
          {'stage': 'NGO_ACCEPTED', 'label': 'Partner NGO Accepted', 'is_completed': true, 'is_current': false},
          {'stage': 'VOLUNTEER_ASSIGNED', 'label': 'Volunteer Assigned', 'is_completed': true, 'is_current': false},
          {'stage': 'PICKUP_VERIFIED', 'label': 'Handover Verified', 'is_completed': true, 'is_current': false},
          {'stage': 'IN_TRANSIT', 'label': 'Food In Transit', 'is_completed': true, 'is_current': true},
          {'stage': 'FOOD_RECEIVED', 'label': 'Food Intake Confirmed', 'is_completed': false, 'is_current': false},
          {'stage': 'BENEFICIARY_DISTRIBUTION', 'label': 'Distribution', 'is_completed': false, 'is_current': false},
          {'stage': 'RESCUE_COMPLETED', 'label': 'Rescue Completed', 'is_completed': false, 'is_current': false},
        ],
        'ngo_capacity_available': true,
        'ngo_current_capacity': 200.0,
        'ngo_max_capacity': 500.0,
      };

      final detail = AdminRescueDetailModel.fromJson(json);
      expect(detail.id, equals(92));
      expect(detail.timeline.length, equals(9));
      expect(detail.timeline[0].stage, equals('DONATION_CREATED'));
      expect(detail.timeline[5].stage, equals('IN_TRANSIT'));
      expect(detail.timeline[5].isCurrent, isTrue);
      expect(detail.ngoCapacityAvailable, isTrue);
      expect(detail.ngoCurrentCapacity, equals(200.0));
      expect(detail.ngoMaxCapacity, equals(500.0));
    });

    test('AdminNgoCapacityModel utilization and status color parsing', () {
      final jsonGreen = {
        'id': 1,
        'organization_name': 'Green Hope Foundation',
        'address': 'Koramangala, Bangalore',
        'current_capacity': 250.0,
        'max_capacity': 500.0,
        'remaining_capacity': 250.0,
        'utilization_percent': 50.0,
        'is_verified': true,
        'is_open': true,
        'status_color': 'GREEN',
      };
      final greenModel = AdminNgoCapacityModel.fromJson(jsonGreen);
      expect(greenModel.utilizationPercent, equals(50.0));
      expect(greenModel.statusColor, equals('GREEN'));

      final jsonRed = {
        'id': 2,
        'organization_name': 'City Relief Center',
        'address': 'Indiranagar, Bangalore',
        'current_capacity': 480.0,
        'max_capacity': 500.0,
        'remaining_capacity': 20.0,
        'utilization_percent': 96.0,
        'is_verified': true,
        'is_open': true,
        'status_color': 'RED',
      };
      final redModel = AdminNgoCapacityModel.fromJson(jsonRed);
      expect(redModel.utilizationPercent, equals(96.0));
      expect(redModel.statusColor, equals('RED'));
    });
  });
}
