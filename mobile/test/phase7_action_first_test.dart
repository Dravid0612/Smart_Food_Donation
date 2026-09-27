import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/widgets/rescue_ring.dart';
import 'package:smart_food_waste_donation/widgets/donation_card.dart';
import 'package:smart_food_waste_donation/screens/donor/quick_rescue_screen.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';

Widget _wrapWithProviders(Widget child, {String language = 'en'}) {
  final lp = LocaleProvider();
  lp.setLanguage(language);
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
      ChangeNotifierProvider<DonationProvider>(create: (_) => DonationProvider()),
    ],
    child: MaterialApp(
      home: Scaffold(
        body: child,
      ),
    ),
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 7 Action-First Experience Tests', () {
    testWidgets('1. RescueRing renders explicit ENDED state when remainingMinutes <= 0', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          Center(
            child: RescueRing.hero(remainingMinutes: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('ENDED'), findsOneWidget);
    });

    testWidgets('2. RescueRing renders compact END when remainingMinutes <= 0 on compact preset', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          Center(
            child: RescueRing.compact(remainingMinutes: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('END'), findsOneWidget);
    });

    testWidgets('3. DonationCard displays ACCEPT RESCUE and PASS buttons for NGO and Volunteer roles', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          DonationCard(
            currentRole: 'ngo',
            foodName: 'Vegetable Rice',
            category: 'Cooked Meals',
            quantity: 25,
            quantityUnit: 'Meals',
            onAccept: () {},
            onReject: () {},
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
      expect(find.text('PASS'), findsOneWidget);
    });

    testWidgets('4. QuickRescueScreen renders camera prompt, advisory disclaimer, and SEND TO RESCUE button', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const QuickRescueScreen(),
        ),
      );
      await tester.pumpAndSettle();

      // Check for camera / scan prompt (appears in app bar and camera hero card)
      expect(find.text('Scan / Take Photo'), findsAtLeastNWidgets(1));

      // Check for advisory disclaimer - never guaranteed safe
      expect(find.textContaining('advisory only'), findsOneWidget);
      expect(find.textContaining('Does not certify food safety'), findsOneWidget);

      // Check prep time options (normal donor understandable)
      expect(find.text('Freshly prepared (within 30m)'), findsOneWidget);
      expect(find.text('About 1 hour ago'), findsOneWidget);

      // Check SEND TO RESCUE primary button
      expect(find.text('SEND TO RESCUE'), findsOneWidget);
    });

    test('5. Phase 7 Action-First strings are localized across English, Tamil, and Hindi', () {
      final keys = [
        'send_to_rescue',
        'accept_rescue',
        'pass',
        'collect_yourself',
        'request_volunteer_btn',
        'action_go_to_pickup',
        'action_arrived',
        'action_verify_otp',
        'action_deliver',
        'ngo_accept_choice_title',
        'ngo_accept_choice_desc',
        'collect_yourself_desc',
        'request_volunteer_desc',
      ];

      for (final code in ['en', 'ta', 'hi']) {
        final dict = LocaleProvider.translations[code];
        expect(dict, isNotNull, reason: 'Dictionary for $code must exist');
        for (final k in keys) {
          expect(dict!.containsKey(k), isTrue, reason: 'Key $k missing in $code dictionary');
          expect(dict[k]!.isNotEmpty, isTrue, reason: 'Key $k cannot be empty in $code dictionary');
        }
      }
    });
  });
}
