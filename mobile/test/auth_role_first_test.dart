import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/screens/auth/login_screen.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Widget createTestWidget() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
        ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
      ],
      child: const MaterialApp(
        home: LoginScreen(),
      ),
    );
  }

  group('Role-First Login Flow Widget Tests', () {
    testWidgets('1. Login screen initially displays 4 role cards and hides credentials', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // App title and role selection header must be visible
      expect(find.text('Smart Food Rescue'), findsOneWidget);
      expect(find.text('Select Your Role'), findsOneWidget);

      // 4 Role cards must be visible
      expect(find.byKey(const Key('role_card_donor')), findsOneWidget);
      expect(find.byKey(const Key('role_card_ngo')), findsOneWidget);
      expect(find.byKey(const Key('role_card_volunteer')), findsOneWidget);
      expect(find.byKey(const Key('role_card_admin')), findsOneWidget);

      // Email and password fields must NOT be visible initially
      expect(find.byKey(const Key('login_email_field')), findsNothing);
      expect(find.byKey(const Key('login_password_field')), findsNothing);
      expect(find.byKey(const Key('login_submit_button')), findsNothing);
    });

    testWidgets('2. Tapping Food Donor reveals donor login form with donor heading and register link', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Tap on Food Donor card
      await tester.tap(find.byKey(const Key('role_card_donor')));
      await tester.pumpAndSettle();

      // Form elements should now be visible
      expect(find.byKey(const Key('login_email_field')), findsOneWidget);
      expect(find.byKey(const Key('login_password_field')), findsOneWidget);
      expect(find.byKey(const Key('login_submit_button')), findsOneWidget);

      // Donor specific heading
      expect(find.text('Food Donor Login'), findsOneWidget);
      expect(find.text('Sign in to donate surplus food and track your rescue impact.'), findsOneWidget);

      // Register link must be present for donor
      expect(find.text('Register'), findsOneWidget);
    });

    testWidgets('3. Tapping Partner NGO reveals NGO login form', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('role_card_ngo')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('login_email_field')), findsOneWidget);
      expect(find.text('Partner NGO Login'), findsOneWidget);
      expect(find.text('Sign in to receive food donations and manage distribution.'), findsOneWidget);
      expect(find.text('Register'), findsOneWidget);
    });

    testWidgets('4. Tapping Volunteer reveals volunteer login form', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('role_card_volunteer')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('login_email_field')), findsOneWidget);
      expect(find.text('Volunteer Login'), findsOneWidget);
      expect(find.text('Sign in to accept rescue tasks and coordinate pickups.'), findsOneWidget);
      expect(find.text('Register'), findsOneWidget);
    });

    testWidgets('5. Tapping Administrator reveals admin login form and HIDES register link', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('role_card_admin')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('login_email_field')), findsOneWidget);
      expect(find.text('Administrator Login'), findsOneWidget);
      expect(find.text('Sign in to manage the food rescue network.'), findsOneWidget);

      // Public registration for admin MUST be hidden
      expect(find.text('Register'), findsNothing);
    });

    testWidgets('6. Role switching dynamically updates heading without page reload', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Tap Donor first
      await tester.tap(find.byKey(const Key('role_card_donor')));
      await tester.pumpAndSettle();
      expect(find.text('Food Donor Login'), findsOneWidget);

      // Switch to NGO
      await tester.tap(find.byKey(const Key('role_card_ngo')));
      await tester.pumpAndSettle();
      expect(find.text('Partner NGO Login'), findsOneWidget);
      expect(find.text('Food Donor Login'), findsNothing);

      // Switch to Admin
      await tester.tap(find.byKey(const Key('role_card_admin')));
      await tester.pumpAndSettle();
      expect(find.text('Administrator Login'), findsOneWidget);
      expect(find.text('Partner NGO Login'), findsNothing);
    });

    testWidgets('7. Form validation for empty and invalid email and password', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Open Donor login
      await tester.tap(find.byKey(const Key('role_card_donor')));
      await tester.pumpAndSettle();

      final formState = tester.state<FormState>(find.byType(Form));
      expect(formState.validate(), isFalse);
      await tester.pumpAndSettle();

      // Form validation errors should show
      expect(find.text('Enter your email'), findsOneWidget);
      expect(find.text('Enter your password'), findsOneWidget);

      // Enter invalid email format
      await tester.enterText(find.byKey(const Key('login_email_field')), 'invalid-email');
      await tester.enterText(find.byKey(const Key('login_password_field')), 'password123');
      expect(formState.validate(), isFalse);
      await tester.pumpAndSettle();

      expect(find.text('Please enter a valid email address.'), findsOneWidget);
    });

    testWidgets('8. Language switching dynamically translates login screen', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Switch language to Tamil
      await tester.tap(find.text('தமிழ்'));
      await tester.pumpAndSettle();

      expect(find.text('ஸ்மார்ட் உணவு மீட்பு'), findsOneWidget);
      expect(find.text('உங்கள் பொறுப்பைத் தேர்வு செய்க'), findsOneWidget);

      // Tap Tamil Donor role
      await tester.tap(find.byKey(const Key('role_card_donor')));
      await tester.pumpAndSettle();

      expect(find.text('உணவு வழங்குநர் உள்நுழைவு'), findsOneWidget);
      expect(find.text('உள்நுழைவு'), findsWidgets);

      // Switch language to Hindi
      await tester.tap(find.text('हिन्दी'));
      await tester.pumpAndSettle();

      expect(find.text('स्मार्ट भोजन बचाव'), findsOneWidget);
      expect(find.text('अपनी भूमिका चुनें'), findsOneWidget);
    });
  });
}
