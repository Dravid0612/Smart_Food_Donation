import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/models/auth_models.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/screens/auth/login_screen.dart';

void main() {
  setUp(() {
    AppLocale.setLocale('en');
  });

  group('Unified LoginScreen Specification Tests', () {
    testWidgets('1. Renders header, inputs, buttons, and language switcher', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        ),
      );

      expect(find.text('Smart Donor'), findsOneWidget);
      expect(find.text('Rescue surplus food before it goes to waste'), findsOneWidget);
      expect(find.text('Phone or email'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Forgot password?'), findsOneWidget);
      expect(find.text('Log in'), findsOneWidget);
      expect(find.text('Create account'), findsOneWidget);

      // Language switcher
      expect(find.text('EN'), findsOneWidget);
      expect(find.text('TA'), findsOneWidget);
      expect(find.text('HI'), findsOneWidget);
    });

    testWidgets('2. Validates empty inputs and prevents submission', (tester) async {
      bool loginCalled = false;
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async {
              loginCalled = true;
              return const AuthResult(role: UserRole.donor, displayName: 'Donor');
            },
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        ),
      );

      // Tap Log in with empty form
      await tester.tap(find.text('Log in'));
      await tester.pumpAndSettle();

      expect(find.text('Enter your phone or email'), findsOneWidget);
      expect(find.text('Enter your password'), findsNWidgets(2));
      expect(loginCalled, isFalse);
    });

    testWidgets('3. Displays AuthException message in AuthErrorBanner on failed auth', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async => throw const AuthException('Invalid credentials.'),
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        ),
      );

      // Enter valid fields
      await tester.enterText(find.byType(TextFormField).first, 'donor@food.org');
      await tester.enterText(find.byType(TextFormField).last, 'wrongpass');
      await tester.tap(find.text('Log in'));
      await tester.pumpAndSettle();

      expect(find.text('Invalid credentials.'), findsOneWidget);
    });

    testWidgets('4. Displays generic network fallback error message on unknown error', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async => throw Exception('Socket connection timeout'),
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        ),
      );

      await tester.enterText(find.byType(TextFormField).first, 'donor@food.org');
      await tester.enterText(find.byType(TextFormField).last, 'secret');
      await tester.tap(find.text('Log in'));
      await tester.pumpAndSettle();

      expect(find.text("Couldn't connect. Check your network and try again."), findsOneWidget);
    });

    testWidgets('5. Language switcher updates active language state and screen text', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        ),
      );

      // Initially in English
      expect(find.text('Log in'), findsOneWidget);

      // Tap Tamil chip
      await tester.tap(find.text('TA'));
      await tester.pumpAndSettle();
      expect(AppLocale.code.value, 'ta');
      expect(find.text('உள்நுழையவும்'), findsOneWidget);

      // Tap Hindi chip
      await tester.tap(find.text('HI'));
      await tester.pumpAndSettle();
      expect(AppLocale.code.value, 'hi');
      expect(find.text('लॉग इन करें'), findsOneWidget);

      // Tap English chip
      await tester.tap(find.text('EN'));
      await tester.pumpAndSettle();
      expect(AppLocale.code.value, 'en');
      expect(find.text('Log in'), findsOneWidget);
    });

    testWidgets('6. Calls onForgotPassword and onNavigateToRegister callbacks', (tester) async {
      bool forgotTapped = false;
      bool registerTapped = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: LoginScreen(
            onLogin: (id, pass) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
            onForgotPassword: () => forgotTapped = true,
            onNavigateToRegister: () => registerTapped = true,
          ),
        ),
      );

      await tester.tap(find.text('Forgot password?'));
      expect(forgotTapped, isTrue);

      await tester.tap(find.text('Create account'));
      expect(registerTapped, isTrue);
    });

    testWidgets('7. Routes correctly based on UserRole and ngoVerified status', (tester) async {
      final routes = <String>[];
      Widget createTestWidget(AuthResult result) {
        return MaterialApp(
          key: UniqueKey(),
          theme: AppTheme.light,
          routes: {
            '/donor': (context) {
              routes.add('/donor');
              return const Scaffold(body: Text('Donor Shell'));
            },
            '/volunteer': (context) {
              routes.add('/volunteer');
              return const Scaffold(body: Text('Volunteer Shell'));
            },
            '/admin': (context) {
              routes.add('/admin');
              return const Scaffold(body: Text('Admin Shell'));
            },
            '/ngo': (context) {
              routes.add('/ngo');
              return const Scaffold(body: Text('NGO Shell'));
            },
            '/ngo/pending': (context) {
              routes.add('/ngo/pending');
              return const Scaffold(body: Text('NGO Pending'));
            },
          },
          home: LoginScreen(
            onLogin: (id, pass) async => result,
            onForgotPassword: () {},
            onNavigateToRegister: () {},
          ),
        );
      }

      // Test donor route
      await tester.pumpWidget(createTestWidget(const AuthResult(role: UserRole.donor, displayName: 'Donor')));
      await tester.enterText(find.byType(TextFormField).first, 'donor@mail.com');
      await tester.enterText(find.byType(TextFormField).last, 'pass1234');
      await tester.tap(find.text('Log in'));
      await tester.pumpAndSettle();
      expect(routes.last, '/donor');

      // Test ngo unverified -> /ngo/pending
      await tester.pumpWidget(createTestWidget(const AuthResult(role: UserRole.ngo, displayName: 'NGO', ngoVerified: false)));
      await tester.enterText(find.byType(TextFormField).first, 'ngo@mail.com');
      await tester.enterText(find.byType(TextFormField).last, 'pass1234');
      await tester.tap(find.text('Log in'));
      await tester.pumpAndSettle();
      expect(routes.last, '/ngo/pending');
    });

    testWidgets('8. No RenderFlex overflow on narrow widths across English, Tamil, and Hindi', (tester) async {
      for (final lang in ['en', 'ta', 'hi']) {
        AppLocale.setLocale(lang);
        tester.view.physicalSize = const Size(320, 640);
        tester.view.devicePixelRatio = 1.0;

        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.light,
            home: LoginScreen(
              onLogin: (id, pass) async => const AuthResult(role: UserRole.donor, displayName: 'Donor'),
              onForgotPassword: () {},
              onNavigateToRegister: () {},
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
      }
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
  });
}

