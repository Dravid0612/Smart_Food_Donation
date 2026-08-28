import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/utils/food_rescue_status_helper.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/widgets/condition_badge.dart';
import 'package:smart_food_waste_donation/widgets/urgency_badge.dart';
import 'package:smart_food_waste_donation/widgets/rescue_ring.dart';
import 'package:smart_food_waste_donation/widgets/donation_card.dart';

Widget _wrapWithLocale(Widget child, {String language = 'en'}) {
  final lp = LocaleProvider();
  lp.setLanguage(language);
  return ChangeNotifierProvider<LocaleProvider>.value(
    value: lp,
    child: MaterialApp(
      home: Scaffold(
        body: child,
      ),
    ),
  );
}

void main() {
  group('1. FoodRescueStatusHelper & 10 State Combinations Unit Tests', () {
    testWidgets('Combination 1: GOOD + FRESH (2h 10m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'GOOD', confidence: 0.92);
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'FRESH', remainingMinutes: 130);
          final win = FoodRescueStatusHelper.getRescueWindow(context, 130);
          final feas = FoodRescueStatusHelper.getRescueFeasibility(context, rawFeasibility: 'RESCUE_FEASIBLE', remainingMinutes: 130);

          expect(vis.label, 'Good visual condition');
          expect(urg.label, 'Fresh');
          expect(win.timeRemainingText, '2h 10m');
          expect(win.isWindowEnded, false);
          expect(feas.isFeasible, true);
          expect(feas.canAcceptDonation, true);
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 2: GOOD + APPROACHING (1h 15m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'GOOD');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'APPROACHING', remainingMinutes: 75);
          final win = FoodRescueStatusHelper.getRescueWindow(context, 75);

          expect(vis.label, 'Good visual condition');
          expect(urg.label, 'Approaching');
          expect(win.timeRemainingText, '1h 15m');
          expect(win.isWindowEnded, false);
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 3: GOOD + URGENT (18m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'GOOD');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'URGENT', remainingMinutes: 18);
          final win = FoodRescueStatusHelper.getRescueWindow(context, 18);

          expect(vis.label, 'Good visual condition');
          expect(urg.label, 'Urgent');
          expect(win.timeRemainingText, '18m');
          expect(win.isWindowEnded, false);
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 4: GOOD + CRITICAL (4m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'GOOD');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'CRITICAL', remainingMinutes: 4);
          final win = FoodRescueStatusHelper.getRescueWindow(context, 4);

          expect(vis.label, 'Good visual condition');
          expect(urg.label, 'Critical');
          expect(win.timeRemainingText, '4m');
          expect(win.isWindowEnded, false);
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 5: GOOD + WINDOW ENDED (0m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'GOOD');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'FRESH', remainingMinutes: 0);
          final win = FoodRescueStatusHelper.getRescueWindow(context, 0);
          final feas = FoodRescueStatusHelper.getRescueFeasibility(context, rawFeasibility: 'RESCUE_FEASIBLE', remainingMinutes: 0);

          expect(vis.label, 'Good visual condition');
          expect(urg.label, 'Rescue window ended');
          expect(urg.isWindowEnded, true);
          expect(win.isWindowEnded, true);
          expect(win.fullDisplayText, 'Rescue window ended');
          expect(feas.canAcceptDonation, false);
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 6: FAIR + APPROACHING (45m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'FAIR');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'APPROACHING', remainingMinutes: 45);

          expect(vis.label, 'Fair visual condition');
          expect(urg.label, 'Approaching');
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 7: FAIR + URGENT (20m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'FAIR');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'URGENT', remainingMinutes: 20);

          expect(vis.label, 'Fair visual condition');
          expect(urg.label, 'Urgent');
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 8: CONCERNING + URGENT (25m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'CONCERNING');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'URGENT', remainingMinutes: 25);

          expect(vis.label, 'Concerning condition');
          expect(urg.label, 'Urgent');
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 9: CONCERNING + CRITICAL (10m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'SPOILAGE_SUSPECTED');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'CRITICAL', remainingMinutes: 10);

          expect(vis.label, 'Spoilage suspected');
          expect(urg.label, 'Critical');
          return const SizedBox.shrink();
        },
      )));
    });

    testWidgets('Combination 10: UNCERTAIN + CRITICAL (15m remaining)', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(Builder(
        builder: (context) {
          final vis = FoodRescueStatusHelper.getVisualCondition(context, 'UNCERTAIN');
          final urg = FoodRescueStatusHelper.getRescueUrgency(context, 'CRITICAL', remainingMinutes: 15);

          expect(vis.label, 'Visual inspection required');
          expect(urg.label, 'Critical');
          return const SizedBox.shrink();
        },
      )));
    });
  });

  group('2. Component Clarity & Contradiction Prevention Tests', () {
    testWidgets('ConditionBadge renders label without confusing percentage in summary mode', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(
        const ConditionBadge(condition: 'GOOD', confidence: 0.88),
      ));

      expect(find.text('Good visual condition'), findsOneWidget);
      expect(find.textContaining('88%'), findsNothing);
    });

    testWidgets('UrgencyBadge renders clean urgency without contradictory time text', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(
        const UrgencyBadge(level: 'URGENT', remainingMinutes: 18),
      ));

      expect(find.text('Urgent'), findsOneWidget);
      expect(find.textContaining('Expired'), findsNothing);
    });

    testWidgets('UrgencyBadge safely displays Rescue window ended when 0m remaining', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(
        const UrgencyBadge(level: 'FRESH', remainingMinutes: 0),
      ));

      expect(find.text('Rescue window ended'), findsOneWidget);
      expect(find.textContaining('Fresh • Expired'), findsNothing);
    });

    testWidgets('RescueRing renders formatted time and label', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWithLocale(
        RescueRing.hero(remainingMinutes: 48, urgencyOverride: 'APPROACHING'),
      ));

      expect(find.text('48m'), findsOneWidget);
    });
  });

  group('3. DonationCard Redesign Hierarchy Tests', () {
    testWidgets('DonationCard displays 5-step hierarchy with separated states', (WidgetTester tester) async {
      final sampleDonation = DonationModel(
        id: 101,
        donorId: 1,
        foodName: 'Vegetable Biryani',
        foodCategory: 'Cooked Food',
        quantity: 500,
        quantityUnit: 'Meals',
        foodSource: 'KNOWN',
        ruleCoverage: 'HIGH',
        classificationSource: 'USER',
        classificationConfidence: 0.95,
        preparationTime: DateTime.now().subtract(const Duration(hours: 4)).toIso8601String(),
        expiryTime: DateTime.now().add(const Duration(minutes: 18)).toIso8601String(),
        pickupAddress: 'Anna Nagar, Chennai',
        previouslyServed: 'No',
        exposureStatus: 'No',
        handlingStatus: 'No',
        remainingMinutes: 18,
        rescueUrgencyLevel: 'URGENT',
        urgencyLevel: 'URGENT',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        aiVisualCondition: 'GOOD',
        aiConfidenceScore: 0.92,
        status: 'pending',
        storageMethod: 'Room Temperature',
        createdAt: DateTime.now().toIso8601String(),
        history: [],
      );

      await tester.pumpWidget(_wrapWithLocale(
        DonationCard(
          donation: sampleDonation,
          onAccept: () {},
          onReject: () {},
        ),
      ));

      // Category + Urgency Pill
      expect(find.text('COOKED FOOD'), findsOneWidget);
      expect(find.text('Urgent'), findsOneWidget);

      // Title + Quantity
      expect(find.text('Vegetable Biryani'), findsOneWidget);
      expect(find.text('500 Meals'), findsOneWidget);

      // Distinct Visual condition & Rescue window lines
      expect(find.text('Good visual condition'), findsOneWidget);
      expect(find.text('18 minutes remaining'), findsOneWidget);
      expect(find.textContaining('Prepared 4h ago'), findsOneWidget);

      // Feasibility
      expect(find.text('Rescue feasible'), findsOneWidget);

      // Action buttons
      expect(find.text('Accept Donation'), findsOneWidget);
      expect(find.text('Decline'), findsOneWidget);
    });

    testWidgets('DonationCard with ended rescue window disables accept action', (WidgetTester tester) async {
      final endedDonation = DonationModel(
        id: 102,
        donorId: 1,
        foodName: 'Mixed Rice',
        foodCategory: 'Cooked Food',
        quantity: 100,
        quantityUnit: 'Meals',
        foodSource: 'KNOWN',
        ruleCoverage: 'HIGH',
        classificationSource: 'USER',
        classificationConfidence: 0.95,
        preparationTime: DateTime.now().subtract(const Duration(hours: 8)).toIso8601String(),
        expiryTime: DateTime.now().subtract(const Duration(minutes: 10)).toIso8601String(),
        pickupAddress: 'T Nagar, Chennai',
        previouslyServed: 'No',
        exposureStatus: 'No',
        handlingStatus: 'No',
        remainingMinutes: 0,
        rescueUrgencyLevel: 'CRITICAL',
        urgencyLevel: 'CRITICAL',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        aiVisualCondition: 'GOOD',
        aiConfidenceScore: 0.88,
        status: 'pending',
        storageMethod: 'Room Temperature',
        createdAt: DateTime.now().subtract(const Duration(hours: 8)).toIso8601String(),
        history: [],
      );

      await tester.pumpWidget(_wrapWithLocale(
        DonationCard(
          donation: endedDonation,
          onAccept: () {},
          onReject: () {},
        ),
      ));

      // Visual condition is Good, but urgency is Rescue window ended
      expect(find.text('Good visual condition'), findsOneWidget);
      expect(find.text('Rescue window ended'), findsWidgets); // Urgency Pill, Feasibility, and Action button
      expect(find.text('Accept Donation'), findsNothing);
    });
  });

  group('4. Trilingual Localization Consistency Tests', () {
    test('English, Tamil, and Hindi accurately express visual condition and urgency', () {
      final lp = LocaleProvider();

      // English
      lp.setLanguage('en');
      expect(lp.translate('urgency_fresh'), 'Fresh');
      expect(lp.translate('urgency_window_ended'), 'Rescue window ended');
      expect(lp.translate('vis_good'), 'Good visual condition');
      expect(lp.translate('feas_rescue_feasible'), 'Rescue feasible');

      // Tamil
      lp.setLanguage('ta');
      expect(lp.translate('urgency_fresh'), 'புதியது');
      expect(lp.translate('urgency_window_ended'), 'மீட்பு காலக்கெடு முடிந்தது');
      expect(lp.translate('vis_good'), 'நல்ல காட்சி நிலை');
      expect(lp.translate('feas_rescue_feasible'), 'மீட்க சாத்தியமானது');

      // Hindi
      lp.setLanguage('hi');
      expect(lp.translate('urgency_fresh'), 'ताज़ा');
      expect(lp.translate('urgency_window_ended'), 'बचाव समय समाप्त');
      expect(lp.translate('vis_good'), 'अच्छी दृश्य स्थिति');
      expect(lp.translate('feas_rescue_feasible'), 'बचाव संभव है');
    });
  });
}
