import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/feedback_model.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/admin_provider.dart';
import 'package:smart_food_waste_donation/widgets/rescue_rating_widget.dart';
import 'package:smart_food_waste_donation/widgets/rescue_feedback_card.dart';
import 'package:smart_food_waste_donation/widgets/report_problem_dialog.dart';
import 'package:smart_food_waste_donation/widgets/trust_indicator_widget.dart';

Widget _wrapWithProviders(Widget child, {LocaleProvider? localeProvider}) {
  final lp = localeProvider ?? LocaleProvider();
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<DonationProvider>(create: (_) => DonationProvider()),
      ChangeNotifierProvider<AdminProvider>(create: (_) => AdminProvider()),
    ],
    child: MaterialApp(
      home: Scaffold(body: child),
    ),
  );
}

void main() {
  group('Rescue Rating & Trust System Widget Tests', () {
    testWidgets('1. RescueRatingWidget displays 5 stars and handles interaction', (WidgetTester tester) async {
      int selectedRating = 3;

      await tester.pumpWidget(
        _wrapWithProviders(
          StatefulBuilder(
            builder: (ctx, setState) => RescueRatingWidget(
              rating: selectedRating,
              onRatingChanged: (val) {
                setState(() => selectedRating = val);
              },
            ),
          ),
        ),
      );

      // Verify star icons
      expect(find.byIcon(Icons.star_rounded), findsNWidgets(3));
      expect(find.byIcon(Icons.star_outline_rounded), findsNWidgets(2));

      // Tap 5th star
      final stars = find.byType(GestureDetector);
      await tester.tap(stars.at(4));
      await tester.pumpAndSettle();

      expect(selectedRating, 5);
      expect(find.byIcon(Icons.star_rounded), findsNWidgets(5));
    });

    testWidgets('2. TrustIndicatorWidget protects new participants with sample size threshold', (WidgetTester tester) async {
      final newVolProfile = ReliabilityProfileModel(
        userId: 10,
        name: 'Rahul V',
        role: 'volunteer',
        totalCompletedRescues: 1,
        totalAcceptedRescues: 1,
        cancellationsCount: 0,
        noShowsCount: 0,
        onTimeRatePercent: 100.0,
        completionRatePercent: 100.0,
        averageServiceRating: 5.0,
        overallReliabilityScore: 95.0,
        trustTier: 'New Volunteer',
        trustBadges: ['New Member'],
        hasSufficientHistory: false,
        sampleSizeThreshold: 3,
        dimensions: [],
      );

      await tester.pumpWidget(
        _wrapWithProviders(
          TrustIndicatorWidget(profile: newVolProfile),
        ),
      );

      // Should display "New Volunteer" tier without punitive rating
      expect(find.text('New Volunteer'), findsOneWidget);
      expect(find.text('New Member'), findsOneWidget);
    });

    testWidgets('3. TrustIndicatorWidget displays established badges and scores', (WidgetTester tester) async {
      final establishedProfile = ReliabilityProfileModel(
        userId: 20,
        name: 'Ananya S',
        role: 'volunteer',
        totalCompletedRescues: 15,
        totalAcceptedRescues: 15,
        cancellationsCount: 0,
        noShowsCount: 0,
        onTimeRatePercent: 96.0,
        completionRatePercent: 100.0,
        averageServiceRating: 4.9,
        overallReliabilityScore: 98.0,
        trustTier: 'Highly Reliable',
        trustBadges: ['Reliable Pickup History', 'Consistent Delivery'],
        hasSufficientHistory: true,
        dimensions: [
          ReliabilityDimensionModel(name: 'Completion Rate', score: 100.0, weight: 0.35, description: 'Rescues completed'),
          ReliabilityDimensionModel(name: 'Punctuality Rate', score: 96.0, weight: 0.25, description: 'On time pickups'),
        ],
      );

      await tester.pumpWidget(
        _wrapWithProviders(
          TrustIndicatorWidget(profile: establishedProfile),
        ),
      );

      expect(find.text('98%'), findsOneWidget);
      expect(find.text('Highly Reliable'), findsOneWidget);
      expect(find.text('Reliable Pickup History'), findsOneWidget);
      expect(find.text('Consistent Delivery'), findsOneWidget);
      expect(find.text('Completion Rate'), findsOneWidget);
    });

    testWidgets('4. RescueFeedbackCard displays completion banner and action buttons', (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const RescueFeedbackCard(
            donationId: 101,
            currentRole: 'donor',
          ),
        ),
      );

      expect(find.text('Rescue Complete ✓'), findsOneWidget);
      expect(find.text('Rate Rescue Experience'), findsOneWidget);
      expect(find.text('Report a Problem'), findsOneWidget);
    });

    testWidgets('5. ReportProblemDialog presents food condition concern disclaimer and options', (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const ReportProblemDialog(
            donationId: 101,
            currentRole: 'ngo',
            initialFoodConditionConcern: true,
          ),
        ),
      );

      // Verify food condition incident report title and legal disclaimer
      expect(find.text('Food Condition Incident Report'), findsOneWidget);
      expect(
        find.textContaining('Submitting this report does not determine whether the food is safe'),
        findsOneWidget,
      );
      expect(find.text('Visible spoilage'), findsOneWidget);
      expect(find.text('Damaged packaging'), findsOneWidget);
    });

    testWidgets('6. Trilingual localization supports EN, TA, and HI', (WidgetTester tester) async {
      final lp = LocaleProvider();

      // Test English
      lp.setLocale(const Locale('en'));
      expect(lp.translate('rate_rescue_experience'), 'Rate Rescue Experience');
      expect(lp.translate('trust_tier_new_vol'), 'New Volunteer');
      expect(lp.translate('issue_cat_volunteer_no_show'), 'Volunteer Did Not Arrive');

      // Test Tamil
      lp.setLocale(const Locale('ta'));
      expect(lp.translate('rate_rescue_experience'), 'மீட்பு அனுபவத்தை மதிப்பிடுங்கள்');
      expect(lp.translate('trust_tier_new_vol'), 'புதிய தன்னார்வலர்');
      expect(lp.translate('issue_cat_volunteer_no_show'), 'தன்னார்வலர் வரவில்லை');

      // Test Hindi
      lp.setLocale(const Locale('hi'));
      expect(lp.translate('rate_rescue_experience'), 'बचाव अनुभव को रेट करें');
      expect(lp.translate('trust_tier_new_vol'), 'नए स्वयंसेवक');
      expect(lp.translate('issue_cat_volunteer_no_show'), 'स्वयंसेवक नहीं पहुंचे');
    });

    testWidgets('7. RescueFeedbackCard displays What went wrong for cancelled/expired rescues', (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const RescueFeedbackCard(
            donationId: 101,
            currentRole: 'donor',
            donationStatus: 'cancelled',
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify "Rescue Incomplete" banner title and "What went wrong with this rescue?" subtitle
      expect(find.text('Rescue Incomplete'), findsOneWidget);
      expect(find.text('What went wrong with this rescue?'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline_rounded), findsOneWidget);
    });

    testWidgets('8. RescueFeedbackCard displays standard rating banner for completed rescues', (WidgetTester tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const RescueFeedbackCard(
            donationId: 101,
            currentRole: 'donor',
            donationStatus: 'completed',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Rescue Complete ✓'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    });
  });
}
