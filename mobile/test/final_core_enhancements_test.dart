import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';

void main() {
  group('Core Enhancement 1: Food-Safety Self-Check Screening', () {
    test('FoodSafetyCheckModel initializes with all 5 affirmations', () {
      final check = FoodSafetyCheckModel();
      expect(check.humanConsumption, isTrue);
      expect(check.hygienicHandling, isTrue);
      expect(check.appropriateStorage, isTrue);
      expect(check.contaminationFree, isTrue);
      expect(check.suitableCondition, isTrue);
      expect(check.isEligible, isTrue);
      expect(check.status, 'PASSED');
    });

    test('FoodSafetyCheckModel correctly serializes and deserializes', () {
      final json = {
        'human_consumption': true,
        'hygienic_handling': false,
        'appropriate_storage': true,
        'contamination_free': true,
        'suitable_condition': true,
        'is_eligible': false,
        'status': 'BLOCKED',
        'failed_declarations': ['hygienic_handling'],
        'warning_message': 'Food safety declaration incomplete.',
        'guidance': 'Ensure clean handling utensils.',
        'disclaimer': 'Advisory screening declaration only.',
      };

      final model = FoodSafetyCheckModel.fromJson(json);
      expect(model.isEligible, isFalse);
      expect(model.status, 'BLOCKED');
      expect(model.failedDeclarations, contains('hygienic_handling'));
      expect(model.guidance, 'Ensure clean handling utensils.');
    });

    test('DonationModel supports safety check fields', () {
      final json = {
        'id': 101,
        'donor_id': 1,
        'food_name': 'Vegetable Biryani',
        'food_category': 'Cooked Food',
        'quantity': 25.0,
        'quantity_unit': 'Meals',
        'preparation_time': '2026-08-24T12:00:00Z',
        'expiry_time': '2026-08-24T16:00:00Z',
        'pickup_address': 'Koramangala, Bengaluru',
        'status': 'pending',
        'created_at': '2026-08-24T12:00:00Z',
        'safety_check_completed': true,
        'safety_check_status': 'PASSED',
        'safety_check_answers': {
          'human_consumption': true,
          'hygienic_handling': true,
          'appropriate_storage': true,
          'contamination_free': true,
          'suitable_condition': true,
        },
      };

      final donation = DonationModel.fromJson(json);
      expect(donation.safetyCheckCompleted, isTrue);
      expect(donation.safetyCheckStatus, 'PASSED');
      expect(donation.safetyCheckAnswers?['human_consumption'], isTrue);
    });
  });

  group('Core Enhancement 2: Real-Time Rescue Tracking & Honest ETA', () {
    test('RescueTrackingModel parses full telemetry payload', () {
      final json = {
        'donation_id': 202,
        'food_name': 'Sambar & Rice',
        'quantity': 40.0,
        'quantity_unit': 'Meals',
        'status': 'en_route',
        'tracking_status': 'EN_ROUTE',
        'tracking_stage': 'EN_ROUTE_PICKUP',
        'stage_label': 'Courier heading to donor',
        'next_action_prompt': 'Courier is 8 min away from pickup.',
        'current_latitude': 12.9716,
        'current_longitude': 77.5946,
        'destination_latitude': 12.9780,
        'destination_longitude': 77.6000,
        'eta_minutes': 8,
        'eta_display': '8 min (Estimated travel time)',
        'distance_km': 2.3,
        'volunteer_name': 'Aravind Kumar',
        'volunteer_phone': '+91 98765 43210',
        'volunteer_vehicle': 'bike',
        'donor_name': 'Hotel Saravana',
        'pickup_address': 'MG Road, Bengaluru',
        'destination_address': 'Seva Trust NGO, Indiranagar',
        'remaining_rescue_window_minutes': 75,
        'feasibility_status': 'RESCUE_FEASIBLE',
        'is_at_risk': false,
        'is_rematched': false,
        'rematch_count': 0,
        'stages_timeline': [
          {
            'stage': 'volunteer_assigned',
            'label': 'Courier Assigned',
            'is_completed': true,
            'is_current': false,
            'timestamp': '2026-08-24T12:05:00Z',
          },
          {
            'stage': 'en_route',
            'label': 'En Route to Donor',
            'is_completed': false,
            'is_current': true,
            'timestamp': '2026-08-24T12:10:00Z',
          },
        ],
      };

      final tracking = RescueTrackingModel.fromJson(json);
      expect(tracking.donationId, 202);
      expect(tracking.trackingStatus, 'EN_ROUTE');
      expect(tracking.etaMinutes, 8);
      expect(tracking.etaDisplay, contains('Estimated travel time'));
      expect(tracking.volunteerVehicle, 'bike');
      expect(tracking.stagesTimeline.length, 2);
      expect(tracking.stagesTimeline.first.isCompleted, isTrue);
      expect(tracking.stagesTimeline.last.isCurrent, isTrue);
    });

    test('DonationModel supports live tracking telemetry fields', () {
      final json = {
        'id': 203,
        'donor_id': 2,
        'food_name': 'Mixed Fruit Salad',
        'food_category': 'Fruits',
        'quantity': 15.0,
        'quantity_unit': 'Kg',
        'preparation_time': '2026-08-24T13:00:00Z',
        'expiry_time': '2026-08-24T15:00:00Z',
        'pickup_address': 'Jayanagar, Bengaluru',
        'status': 'in_transit',
        'created_at': '2026-08-24T13:00:00Z',
        'tracking_latitude': 12.9352,
        'tracking_longitude': 77.6245,
        'current_eta_minutes': 14.0,
        'current_distance_km': 3.8,
        'tracking_status': 'IN_TRANSIT',
      };

      final donation = DonationModel.fromJson(json);
      expect(donation.currentEtaMinutes, 14.0);
      expect(donation.currentDistanceKm, 3.8);
      expect(donation.trackingStatus, 'IN_TRANSIT');
    });
  });

  group('Core Enhancement 3: Dynamic Rematching & Reassignment', () {
    test('DonationModel parses dynamic rematch fields', () {
      final json = {
        'id': 301,
        'donor_id': 3,
        'food_name': 'Paneer Butter Masala',
        'food_category': 'Cooked Food',
        'quantity': 30.0,
        'quantity_unit': 'Meals',
        'preparation_time': '2026-08-24T14:00:00Z',
        'expiry_time': '2026-08-24T16:30:00Z',
        'pickup_address': 'HSR Layout, Bengaluru',
        'status': 'assigned',
        'created_at': '2026-08-24T14:00:00Z',
        'is_rematched': true,
        'rematch_count': 1,
        'rematch_reason': 'Previous courier delayed / traffic congestion',
        'previous_volunteer_id': 12,
        'previous_volunteer_name': 'Karthik S',
        'assigned_volunteer_id': 18,
        'volunteer_name': 'Ramesh P',
      };

      final donation = DonationModel.fromJson(json);
      expect(donation.isRematched, isTrue);
      expect(donation.rematchCount, 1);
      expect(donation.previousVolunteerName, 'Karthik S');
      expect(donation.volunteerName, 'Ramesh P');
      expect(donation.rematchReason, contains('traffic congestion'));
    });
  });

  group('Trilingual Localization Coverage (EN, TA, HI)', () {
    final keys = [
      'safety_check_title',
      'safety_check_subtitle',
      'safety_check_disclaimer',
      'safety_q1_title',
      'safety_q2_title',
      'safety_q3_title',
      'safety_q4_title',
      'safety_q5_title',
      'safety_all_affirm_passed',
      'safety_blocked_msg',
      'tracking_title',
      'tracking_eta_label',
      'tracking_battery_note',
      'rematch_banner_title',
      'rematch_banner_desc',
      'volunteer_reassigned_title',
      'volunteer_reassigned_desc',
      'vol_action_start_pickup',
      'vol_action_verify_otp',
      'vol_action_start_delivery',
      'vol_action_confirm_handover',
    ];

    test('English translations have non-empty values for all new keys', () {
      for (final key in keys) {
        final val = LocaleProvider.translations['en']?[key];
        expect(val, isNotNull, reason: 'Missing EN translation for $key');
        expect(val, isNotEmpty, reason: 'Empty EN translation for $key');
      }
    });

    test('Tamil translations have non-empty values for all new keys', () {
      for (final key in keys) {
        final val = LocaleProvider.translations['ta']?[key];
        expect(val, isNotNull, reason: 'Missing TA translation for $key');
        expect(val, isNotEmpty, reason: 'Empty TA translation for $key');
      }
    });

    test('Hindi translations have non-empty values for all new keys', () {
      for (final key in keys) {
        final val = LocaleProvider.translations['hi']?[key];
        expect(val, isNotNull, reason: 'Missing HI translation for $key');
        expect(val, isNotEmpty, reason: 'Empty HI translation for $key');
      }
    });
  });
}
