import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/models/auth_models.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/screens/auth/register_screen.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    AppLocale.setLocale('en');
  });

  group('Unified RegisterScreen Specification Tests', () {
    testWidgets('1. Renders role selector, inputs, and submit button', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
          ),
        ),
      );

      expect(find.text('Create account'), findsNWidgets(2)); // Heading & Button
      expect(find.text('Choose the role that matches what you do'), findsOneWidget);
      expect(find.text('Full name'), findsOneWidget);
      expect(find.text('Phone or email'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Business name'), findsOneWidget); // Default role is Donor
    });

    testWidgets('2. Role selection dynamically switches role-specific extra field', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
          ),
        ),
      );

      // Default Donor shows Business name
      expect(find.text('Business name'), findsOneWidget);

      // Switch to NGO
      await tester.tap(find.text('NGO'));
      await tester.pumpAndSettle();

      expect(find.text('Organisation name'), findsOneWidget);
      expect(find.text('Business name'), findsNothing);

      // Switch to Volunteer
      await tester.tap(find.text('Volunteer'));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle type'), findsOneWidget);
      expect(find.text('Walking'), findsOneWidget);
      expect(find.text('Bike'), findsOneWidget);
      expect(find.text('Car'), findsOneWidget);
      expect(find.text('Van'), findsOneWidget);
    });

    testWidgets('3. Form validation requires valid fields and min 8 char password', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
          ),
        ),
      );

      // Tap submit with empty fields
      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(find.text('Enter your name'), findsOneWidget);
      expect(find.text('Enter a phone number or email'), findsOneWidget);
      // Both hint and validation error match 'Create a password'
      expect(find.text('Create a password'), findsNWidgets(2));
      expect(find.text('This field is required'), findsOneWidget);

      // Test short password (< 8 chars)
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'short');
      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(find.text('Use at least 8 characters'), findsOneWidget);
    });

    testWidgets('4. Successful submission constructs RegisterRequest and invokes onRegister with stable vehicle key', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      RegisterRequest? capturedRequest;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async {
              capturedRequest = req;
              return const AuthResult(role: UserRole.volunteer, displayName: 'Ramesh');
            },
          ),
        ),
      );

      // Select Volunteer role
      await tester.tap(find.text('Volunteer'));
      await tester.pumpAndSettle();

      // Select Car
      await tester.tap(find.text('Car'));
      await tester.pumpAndSettle();

      // Fill in inputs
      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'Ramesh Kumar');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'ramesh@volunteer.org');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'securePassword123');

      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pump();

      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.role, UserRole.volunteer);
      expect(capturedRequest!.name, 'Ramesh Kumar');
      expect(capturedRequest!.contact, 'ramesh@volunteer.org');
      expect(capturedRequest!.password, 'securePassword123');
      // Verifies stable English vehicle key
      expect(capturedRequest!.extraField, 'car');
    });

    testWidgets('5. Displays AuthException message in AuthErrorBanner on error', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => throw const AuthException('An account with this email already exists.'),
          ),
        ),
      );

      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'Anita Roy');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'anita@org.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'password888');
      await tester.enterText(find.widgetWithText(TextFormField, 'Taj Hotel kitchen'), 'Anita Bakery');

      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(find.text('An account with this email already exists.'), findsOneWidget);
    });

    testWidgets('6. Rebuilds reactively when AppLocale.code changes', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
          ),
        ),
      );

      expect(find.text('Full name'), findsOneWidget);

      // Change locale to Tamil
      AppLocale.setLocale('ta');
      await tester.pumpAndSettle();
      expect(find.text('முழுப் பெயர்'), findsOneWidget);

      // Change locale to Hindi
      AppLocale.setLocale('hi');
      await tester.pumpAndSettle();
      expect(find.text('पूरा नाम'), findsOneWidget);
    });
  });
}
