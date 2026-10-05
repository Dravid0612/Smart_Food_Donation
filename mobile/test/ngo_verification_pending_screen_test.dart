import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_verification_pending_screen.dart';

void main() {
  setUp(() {
    AppLocale.setLocale('en');
  });

  group('NgoVerificationPendingScreen Specification Tests', () {
    testWidgets('1. Renders pending icon, organization name, review copy, and buttons', (tester) async {
      bool logoutCalled = false;
      bool refreshCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: NgoVerificationPendingScreen(
            organisationName: 'Karunai Care Foundation',
            onLogout: () => logoutCalled = true,
            onRefreshStatus: () async => refreshCalled = true,
          ),
        ),
      );

      // Verify icon
      expect(find.byIcon(Icons.schedule_outlined), findsOneWidget);

      // Verify headings and copy
      expect(find.text('Verification pending'), findsOneWidget);
      expect(
        find.text(
          'Karunai Care Foundation is under review. You can accept '
          'donations once an admin verifies your organisation.',
        ),
        findsOneWidget,
      );

      // Verify buttons
      expect(find.text('Check status'), findsOneWidget);
      expect(find.text('Log out'), findsOneWidget);

      // Verify no bottom navigation bar is present
      expect(find.byType(BottomNavigationBar), findsNothing);
      expect(find.byType(NavigationBar), findsNothing);

      // Test callbacks
      await tester.tap(find.text('Check status'));
      expect(refreshCalled, isTrue);

      await tester.tap(find.text('Log out'));
      expect(logoutCalled, isTrue);
    });

    testWidgets('2. Check status button is omitted when onRefreshStatus is null', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: NgoVerificationPendingScreen(
            organisationName: 'Green Hope Trust',
            onLogout: () {},
            onRefreshStatus: null,
          ),
        ),
      );

      expect(find.text('Check status'), findsNothing);
      expect(find.text('Log out'), findsOneWidget);
    });

    testWidgets('3. Reactively reflects language switch in Tamil and Hindi', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: NgoVerificationPendingScreen(
            organisationName: 'Green Hope Foundation',
            onLogout: () {},
            onRefreshStatus: () async {},
          ),
        ),
      );

      expect(find.text('Verification pending'), findsOneWidget);

      // Switch to Tamil
      AppLocale.setLocale('ta');
      await tester.pumpAndSettle();

      expect(find.text('சரிபார்ப்பு நிலுவையில் உள்ளது'), findsOneWidget);
      expect(find.text('நிலையைச் சரிபார்க்கவும்'), findsOneWidget);
      expect(find.text('வெளியேறு'), findsOneWidget);
      expect(
        find.text(
          'Green Hope Foundation நிறுவனம் நிர்வாகியால் சரிபார்க்கப்படுகிறது. சரிபார்ப்பு முடிந்தவுடன் நீங்கள் நன்கொடைகளை ஏற்கலாம்.',
        ),
        findsOneWidget,
      );

      // Switch to Hindi
      AppLocale.setLocale('hi');
      await tester.pumpAndSettle();

      expect(find.text('सत्यापन लंबित है'), findsOneWidget);
      expect(find.text('स्थिति जांचें'), findsOneWidget);
      expect(find.text('लॉग आउट करें'), findsOneWidget);
      expect(
        find.text(
          'Green Hope Foundation की समीक्षा की जा रही है। एडमिन द्वारा सत्यापन के बाद आप दान स्वीकार कर सकेंगे।',
        ),
        findsOneWidget,
      );
    });
  });
}
