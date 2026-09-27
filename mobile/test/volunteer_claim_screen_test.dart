import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_claim_screen.dart';
import 'package:smart_food_waste_donation/providers/volunteer_task_provider.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';

class MockVolunteerTaskProvider extends VolunteerTaskProvider {
  final RescueClaimPreviewModel? mockPreview;
  final RescueClaimAcceptResult? mockAcceptResult;
  final bool shouldFailPreview;
  final bool shouldFailAccept;

  MockVolunteerTaskProvider({
    this.mockPreview,
    this.mockAcceptResult,
    this.shouldFailPreview = false,
    this.shouldFailAccept = false,
  });

  @override
  Future<RescueClaimPreviewModel?> fetchClaimPreview(String token) async {
    if (shouldFailPreview) return null;
    return mockPreview ??
        RescueClaimPreviewModel(
          claimToken: token,
          donationId: 101,
          foodName: 'Paneer Biryani',
          foodCategory: 'Cooked Food',
          quantity: 50.0,
          quantityUnit: 'Meals',
          pickupNeighborhood: 'Koramangala 5th Block area',
          remainingMinutes: 48,
          urgencyLevel: 'URGENT',
          isFeasible: true,
          expiresAt: DateTime.now().add(const Duration(minutes: 48)).toIso8601String(),
          status: 'pending',
        );
  }

  @override
  Future<RescueClaimAcceptResult?> acceptClaim({
    required String token,
    required String name,
    required String phone,
    String vehicleType = 'bike',
    int carryingCapacity = 50,
    double? currentLat,
    double? currentLon,
  }) async {
    if (shouldFailAccept) return null;
    return mockAcceptResult ??
        RescueClaimAcceptResult(
          accessToken: 'mock_jwt_token_123',
          user: {'id': 202, 'name': name, 'role': 'volunteer'},
          assignmentId: 303,
          donationId: 101,
          status: 'volunteer_assigned',
          pickupAddress: '142, 5th Block, 80 Feet Road, Koramangala',
          currentEtaMinutes: 12.0,
          remainingMinutes: 48,
          urgencyLevel: 'URGENT',
          message: 'Rescue claimed successfully.',
        );
  }
}

Widget _wrapWithProviders(
  Widget child, {
  LocaleProvider? localeProvider,
  String language = 'en',
  MockVolunteerTaskProvider? taskProvider,
}) {
  final lp = localeProvider ?? LocaleProvider();
  if (localeProvider == null && language != 'en') {
    lp.setLanguage(language);
  }
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
      ChangeNotifierProvider<VolunteerTaskProvider>(
        create: (_) => taskProvider ?? MockVolunteerTaskProvider(),
      ),
    ],
    child: MaterialApp(
      home: child,
    ),
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  group('Frictionless Volunteer Claim Screen Tests', () {
    testWidgets('1. Displays public rescue preview with category, meals, area and countdown', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('FOOD RESCUE'), findsOneWidget);
      expect(find.text('Paneer Biryani'), findsOneWidget);
      expect(find.text('50 Meals'), findsOneWidget);
      expect(find.text('Koramangala 5th Block area'), findsOneWidget);
      expect(find.text('48 minutes remaining'), findsOneWidget);
      expect(find.byKey(const Key('accept_rescue_btn')), findsOneWidget);
      expect(find.byKey(const Key('pass_rescue_btn')), findsOneWidget);
    });

    testWidgets('2. Tapping Accept transitions to minimal identity input form', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Accept
      await tester.tap(find.byKey(const Key('accept_rescue_btn')));
      await tester.pumpAndSettle();

      expect(find.text('Quick Volunteer Claim'), findsOneWidget);
      expect(find.byKey(const Key('volunteer_name_field')), findsOneWidget);
      expect(find.byKey(const Key('volunteer_phone_field')), findsOneWidget);
      expect(find.byKey(const Key('continue_claim_btn')), findsOneWidget);
    });

    testWidgets('3. Submitting empty form triggers input validation error', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('accept_rescue_btn')));
      await tester.pumpAndSettle();

      // Tap Continue with empty fields
      await tester.tap(find.byKey(const Key('continue_claim_btn')));
      await tester.pumpAndSettle();

      expect(find.text('Please enter your name'), findsOneWidget);
    });

    testWidgets('4. Submitting valid name and phone transitions to Rescue Accepted screen', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('accept_rescue_btn')));
      await tester.pumpAndSettle();

      // Enter name & phone
      await tester.enterText(find.byKey(const Key('volunteer_name_field')), 'Ravi Shankar');
      await tester.enterText(find.byKey(const Key('volunteer_phone_field')), '+919876543210');
      await tester.pumpAndSettle();

      // Tap Continue
      await tester.tap(find.byKey(const Key('continue_claim_btn')));
      await tester.pumpAndSettle();

      // Verify confirmation screen
      expect(find.text('RESCUE ACCEPTED ✓'), findsOneWidget);
      expect(find.text('142, 5th Block, 80 Feet Road, Koramangala'), findsOneWidget);
      expect(find.text('~12 mins'), findsOneWidget);
      expect(find.byKey(const Key('start_pickup_btn')), findsOneWidget);
    });

    testWidgets('5. Displays error view when token is invalid or expired', (tester) async {
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'invalid_token_999'),
          taskProvider: MockVolunteerTaskProvider(shouldFailPreview: true),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Rescue Unavailable'), findsOneWidget);
      expect(find.byIcon(Icons.link_off_rounded), findsOneWidget);
    });

    testWidgets('6. Supports Tamil and Hindi localization rendering', (tester) async {
      // Test Tamil
      SharedPreferences.setMockInitialValues({'selected_language': 'ta'});
      final lpTa = LocaleProvider();
      await lpTa.setLanguage('ta');
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
          localeProvider: lpTa,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('உணவு மீட்பு'), findsOneWidget);
      expect(find.text('மீட்பை ஏற்கவும்'), findsOneWidget);
      expect(find.text('தவிர்க்கவும்'), findsOneWidget);

      // Test Hindi
      SharedPreferences.setMockInitialValues({'selected_language': 'hi'});
      final lpHi = LocaleProvider();
      await lpHi.setLanguage('hi');
      await tester.pumpWidget(
        _wrapWithProviders(
          const VolunteerClaimScreen(token: 'valid_test_token_123'),
          localeProvider: lpHi,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('भोजन बचाव'), findsOneWidget);
      expect(find.text('बचाव स्वीकारें'), findsOneWidget);
      expect(find.text('छोड़ें'), findsOneWidget);
    });
  });
}
