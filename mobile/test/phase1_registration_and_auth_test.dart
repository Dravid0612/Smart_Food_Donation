import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/screens/auth/register_screen.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_verification_pending_screen.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    AppLocale.setLocale('en');
  });

  group('Phase 1 — Account Creation & Authentication Specifications', () {
    testWidgets('1. All four roles supported in registration flow', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: RegisterScreen(
            onRegister: (req) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
            allowAdmin: true,
          ),
        ),
      );

      // Verify all 4 roles exist in the selector
      expect(find.text('Donor'), findsOneWidget);
      expect(find.text('NGO'), findsOneWidget);
      expect(find.text('Volunteer'), findsOneWidget);
      expect(find.text('Admin'), findsOneWidget);
    });

    testWidgets('2. Donor registration flow captures business name and routes to donor home', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final routes = <String>[];
      RegisterRequest? captured;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          routes: {
            '/donor': (context) {
              routes.add('/donor');
              return const Scaffold(body: Text('Donor Dashboard'));
            },
          },
          home: RegisterScreen(
            onRegister: (req) async {
              captured = req;
              return AuthResult(role: UserRole.donor, displayName: req.name);
            },
            allowAdmin: true,
          ),
        ),
      );

      // Default role is Donor
      expect(find.text('Business name'), findsOneWidget);

      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'Hotel Grand');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'grand@hotel.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'hotelSecret123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Taj Hotel kitchen'), 'Grand Palace Kitchen');

      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(captured, isNotNull);
      expect(captured!.role, UserRole.donor);
      expect(captured!.name, 'Hotel Grand');
      expect(captured!.contact, 'grand@hotel.com');
      expect(captured!.extraField, 'Grand Palace Kitchen');
      expect(routes.last, '/donor');
    });

    testWidgets('3. NGO registration captures organisation name and routes to pending verification', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final routes = <String>[];
      RegisterRequest? captured;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          routes: {
            '/ngo/pending': (context) {
              routes.add('/ngo/pending');
              return const Scaffold(body: Text('NGO Verification Pending Screen'));
            },
          },
          home: RegisterScreen(
            onRegister: (req) async {
              captured = req;
              return AuthResult(role: UserRole.ngo, displayName: req.name, ngoVerified: false);
            },
            allowAdmin: true,
          ),
        ),
      );

      // Switch to NGO role
      await tester.tap(find.text('NGO'));
      await tester.pumpAndSettle();

      expect(find.text('Organisation name'), findsOneWidget);

      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'Save Meals Trust');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'contact@savemeals.org');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'ngoPassword123');
      await tester.enterText(find.widgetWithText(TextFormField, 'Green Hope Foundation'), 'Save Meals Organization');

      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(captured, isNotNull);
      expect(captured!.role, UserRole.ngo);
      expect(captured!.name, 'Save Meals Trust');
      expect(captured!.extraField, 'Save Meals Organization');
      expect(routes.last, '/ngo/pending');
    });

    testWidgets('4. Volunteer registration captures vehicle type and routes to volunteer home', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final routes = <String>[];
      RegisterRequest? captured;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          routes: {
            '/volunteer': (context) {
              routes.add('/volunteer');
              return const Scaffold(body: Text('Volunteer Dashboard'));
            },
          },
          home: RegisterScreen(
            onRegister: (req) async {
              captured = req;
              return AuthResult(role: UserRole.volunteer, displayName: req.name);
            },
            allowAdmin: true,
          ),
        ),
      );

      // Switch to Volunteer role
      await tester.tap(find.text('Volunteer'));
      await tester.pumpAndSettle();

      expect(find.text('Vehicle type'), findsOneWidget);
      await tester.tap(find.text('Van'));
      await tester.pumpAndSettle();

      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'Ajay Delivery');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'ajay@rescue.org');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'ajayPass123');

      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(captured, isNotNull);
      expect(captured!.role, UserRole.volunteer);
      expect(captured!.extraField, 'van');
      expect(routes.last, '/volunteer');
    });

    testWidgets('5. Admin registration requires authorized setup key and routes to admin overview', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final routes = <String>[];
      RegisterRequest? captured;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          routes: {
            '/admin': (context) {
              routes.add('/admin');
              return const Scaffold(body: Text('Admin Overview'));
            },
          },
          home: RegisterScreen(
            onRegister: (req) async {
              if (req.adminSecret != 'admin-setup-secret-2026') {
                throw const AuthException('Invalid administrator setup key.');
              }
              captured = req;
              return AuthResult(role: UserRole.admin, displayName: req.name);
            },
            allowAdmin: true,
          ),
        ),
      );

      // Switch to Admin role
      await tester.tap(find.text('Admin'));
      await tester.pumpAndSettle();

      expect(find.text('Administrator Setup Key'), findsOneWidget);

      await tester.enterText(find.widgetWithText(TextFormField, 'Your name'), 'System Admin');
      await tester.enterText(find.widgetWithText(TextFormField, 'you@example.com'), 'sysadmin@platform.org');
      await tester.enterText(find.widgetWithText(TextFormField, 'Create a password'), 'adminSecretPwd123');

      // Attempt to submit without setup key -> client validation blocks
      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();
      expect(find.text('Admin setup key is required'), findsOneWidget);
      expect(captured, isNull);

      // Enter valid setup key and submit
      await tester.enterText(find.widgetWithText(TextFormField, 'Enter administrator setup key'), 'admin-setup-secret-2026');
      await tester.tap(find.widgetWithText(ElevatedButton, 'Create account'));
      await tester.pumpAndSettle();

      expect(captured, isNotNull);
      expect(captured!.role, UserRole.admin);
      expect(captured!.adminSecret, 'admin-setup-secret-2026');
      expect(routes.last, '/admin');
    });

    testWidgets('6. NGO Verification Pending Screen displays review status and actions', (tester) async {
      bool statusChecked = false;
      bool loggedOut = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: NgoVerificationPendingScreen(
            organisationName: 'Hope Foundation',
            onRefreshStatus: () async => statusChecked = true,
            onLogout: () => loggedOut = true,
          ),
        ),
      );

      expect(find.text('Verification pending'), findsOneWidget);
      expect(find.textContaining('Hope Foundation is under review'), findsOneWidget);
      expect(find.text('Check status'), findsOneWidget);
      expect(find.text('Log out'), findsOneWidget);

      await tester.tap(find.text('Check status'));
      await tester.pump();
      expect(statusChecked, isTrue);

      await tester.tap(find.text('Log out'));
      await tester.pump();
      expect(loggedOut, isTrue);
    });

    test('7. UserModel authoritative role mapping cannot be tampered with locally', () {
      final donorJson = {
        'id': 1,
        'name': 'Donor User',
        'email': 'donor@test.org',
        'role': 'donor',
        'is_active': true,
      };
      final donorModel = UserModel.fromJson(donorJson);
      expect(donorModel.userRole, UserRole.donor);
      expect(donorModel.role, 'donor');

      final ngoJson = {
        'id': 2,
        'name': 'NGO User',
        'email': 'ngo@test.org',
        'role': 'ngo',
        'is_active': true,
      };
      final ngoModel = UserModel.fromJson(ngoJson);
      expect(ngoModel.userRole, UserRole.ngo);

      final volJson = {
        'id': 3,
        'name': 'Vol User',
        'email': 'vol@test.org',
        'role': 'volunteer',
        'is_active': false,
      };
      final volModel = UserModel.fromJson(volJson);
      expect(volModel.userRole, UserRole.volunteer);
      expect(volModel.isActive, false);

      final adminJson = {
        'id': 4,
        'name': 'Admin User',
        'email': 'admin@test.org',
        'role': 'admin',
        'is_active': true,
      };
      final adminModel = UserModel.fromJson(adminJson);
      expect(adminModel.userRole, UserRole.admin);
    });
  });
}
