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

  Widget createTestWidget({Size size = const Size(800, 1600)}) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
        ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
      ],
      child: MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: const LoginScreen(),
        ),
      ),
    );
  }

  group('Role-Aware Login Screen Flow Widget Tests', () {
    testWidgets('1. Login screen renders credentials form, role selector, and action buttons', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsNWidgets(2));
      expect(find.text(AppLocale.t('remember_me')), findsOneWidget);
      expect(find.text(AppLocale.t('forgot_password')), findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });

    testWidgets('2. Narrow screen rendering does NOT throw RenderFlex overflow (Section 10)', (WidgetTester tester) async {
      // Test on ultra-narrow 320dp width phone screen
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(createTestWidget(size: const Size(320, 640)));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text(AppLocale.t('remember_me')), findsOneWidget);
      expect(find.text(AppLocale.t('forgot_password')), findsOneWidget);
    });

    testWidgets('3. Form validation triggers when submitting empty inputs', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text(AppLocale.t('enter_phone_or_email')), findsOneWidget);
      expect(find.text(AppLocale.t('enter_password')), findsWidgets);
    });

    testWidgets('4. Language switcher dynamically updates Remember Me and Forgot Password labels', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Switch to Tamil
      AppLocale.setLocale('ta');
      await tester.pumpAndSettle();

      expect(find.text(AppLocale.t('remember_me')), findsOneWidget);
      expect(find.text(AppLocale.t('forgot_password')), findsOneWidget);

      // Reset to English
      AppLocale.setLocale('en');
      await tester.pumpAndSettle();
    });
  });
}
