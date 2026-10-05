import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/auth_models.dart';
import 'package:smart_food_waste_donation/widgets/auth/role_selector.dart';

void main() {
  setUp(() {
    AppLocale.setLocale('en');
  });

  group('RoleSelector Specification Tests', () {
    testWidgets('Renders 3 public registration options (Donor, NGO, Volunteer) and excludes Admin', (tester) async {
      UserRole currentRole = UserRole.donor;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: StatefulBuilder(
              builder: (context, setState) {
                return RoleSelector(
                  selected: currentRole,
                  onChanged: (role) => setState(() => currentRole = role),
                );
              },
            ),
          ),
        ),
      );

      // Verify the 3 roles exist
      expect(find.text('Donor'), findsOneWidget);
      expect(find.text('NGO'), findsOneWidget);
      expect(find.text('Volunteer'), findsOneWidget);

      // Verify Admin is NOT an option for registration
      expect(find.text('Admin'), findsNothing);

      // Verify icons
      expect(find.byIcon(Icons.storefront_outlined), findsOneWidget);
      expect(find.byIcon(Icons.apartment_outlined), findsOneWidget);
      expect(find.byIcon(Icons.pedal_bike_outlined), findsOneWidget);
    });

    testWidgets('Tapping on a role updates selection and notifies onChanged', (tester) async {
      UserRole currentRole = UserRole.donor;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: StatefulBuilder(
              builder: (context, setState) {
                return RoleSelector(
                  selected: currentRole,
                  onChanged: (role) => setState(() => currentRole = role),
                );
              },
            ),
          ),
        ),
      );

      // Tap on NGO chip
      await tester.tap(find.text('NGO'));
      await tester.pumpAndSettle();
      expect(currentRole, UserRole.ngo);

      // Tap on Volunteer chip
      await tester.tap(find.text('Volunteer'));
      await tester.pumpAndSettle();
      expect(currentRole, UserRole.volunteer);

      // Tap on Donor chip
      await tester.tap(find.text('Donor'));
      await tester.pumpAndSettle();
      expect(currentRole, UserRole.donor);
    });

    testWidgets('Renders localized role labels in Tamil and Hindi', (tester) async {
      UserRole currentRole = UserRole.donor;

      // Switch to Tamil
      AppLocale.setLocale('ta');

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: RoleSelector(
              selected: currentRole,
              onChanged: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('நன்கொடையாளர்'), findsOneWidget);
      expect(find.text('NGO'), findsOneWidget);
      expect(find.text('தன்னார்வலர்'), findsOneWidget);

      // Switch to Hindi
      AppLocale.setLocale('hi');
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: RoleSelector(
              selected: currentRole,
              onChanged: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('दानकर्ता'), findsOneWidget);
      expect(find.text('NGO'), findsOneWidget);
      expect(find.text('स्वयंसेवक'), findsOneWidget);
    });
  });
}
