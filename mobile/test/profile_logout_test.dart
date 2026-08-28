import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/volunteer_task_provider.dart';
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';

Widget createTestableProfileScreen({required UserModel user}) {
  final auth = AuthProvider();
  auth.setCurrentUserForTesting(user);
  return MultiProvider(
    providers: [
      ChangeNotifierProvider(create: (_) => LocaleProvider()),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider(create: (_) => VolunteerTaskProvider()),
    ],
    child: MaterialApp(
      theme: AppTheme.lightTheme,
      home: const ProfileScreen(),
    ),
  );
}

void main() {
  group('Profile Screen Logout Tests for All 4 Roles', () {
    testWidgets('1. Food Donor profile page displays logout button and dialog', (tester) async {
      final donorUser = UserModel(
        id: 1,
        name: 'Taj Palace Hotel',
        email: 'donor@example.com',
        role: 'donor',
        phone: '+91 9876543210',
        address: 'MG Road, Bengaluru',
        isActive: true,
      );

      await tester.pumpWidget(createTestableProfileScreen(user: donorUser));
      await tester.pumpAndSettle();

      expect(find.text('Taj Palace Hotel'), findsOneWidget);
      expect(find.byIcon(Icons.logout_rounded), findsAtLeastNWidgets(1));

      // Tap logout button at the bottom of the profile page
      final logoutButton = find.widgetWithText(OutlinedButton, 'Log Out');
      expect(logoutButton, findsOneWidget);
      await tester.ensureVisible(logoutButton);
      await tester.tap(logoutButton);
      await tester.pumpAndSettle();

      // Verify confirmation dialog appears
      expect(find.text('Are you sure you want to log out?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);

      // Cancel dialog
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(find.text('Are you sure you want to log out?'), findsNothing);
    });

    testWidgets('2. Partner NGO profile page displays logout button and dialog', (tester) async {
      final ngoUser = UserModel(
        id: 2,
        name: 'Akshaya Patra Foundation',
        email: 'ngo@example.com',
        role: 'ngo',
        phone: '+91 9876500000',
        address: 'Rajajinagar, Bengaluru',
        isActive: true,
      );

      await tester.pumpWidget(createTestableProfileScreen(user: ngoUser));
      await tester.pumpAndSettle();

      expect(find.text('Akshaya Patra Foundation'), findsOneWidget);
      expect(find.byIcon(Icons.logout_rounded), findsAtLeastNWidgets(1));

      final logoutButton = find.widgetWithText(OutlinedButton, 'Log Out');
      expect(logoutButton, findsOneWidget);
      await tester.ensureVisible(logoutButton);
      await tester.tap(logoutButton);
      await tester.pumpAndSettle();

      expect(find.text('Are you sure you want to log out?'), findsOneWidget);
    });

    testWidgets('3. Volunteer Hero profile page displays logout button and dialog', (tester) async {
      final volunteerUser = UserModel(
        id: 3,
        name: 'Rahul Kumar',
        email: 'volunteer@example.com',
        role: 'volunteer',
        phone: '+91 9876511111',
        address: 'Koramangala, Bengaluru',
        isActive: true,
      );

      await tester.pumpWidget(createTestableProfileScreen(user: volunteerUser));
      await tester.pumpAndSettle();

      expect(find.text('Rahul Kumar'), findsOneWidget);
      expect(find.byIcon(Icons.logout_rounded), findsAtLeastNWidgets(1));

      final logoutButton = find.widgetWithText(OutlinedButton, 'Log Out');
      expect(logoutButton, findsOneWidget);
      await tester.ensureVisible(logoutButton);
      await tester.tap(logoutButton);
      await tester.pumpAndSettle();

      expect(find.text('Are you sure you want to log out?'), findsOneWidget);
    });

    testWidgets('4. Administrator profile page displays logout button and dialog', (tester) async {
      final adminUser = UserModel(
        id: 4,
        name: 'System Operations Lead',
        email: 'admin@example.com',
        role: 'admin',
        phone: '+91 9876599999',
        address: 'Command Center, Bengaluru',
        isActive: true,
      );

      await tester.pumpWidget(createTestableProfileScreen(user: adminUser));
      await tester.pumpAndSettle();

      expect(find.text('System Operations Lead'), findsOneWidget);
      expect(find.byIcon(Icons.logout_rounded), findsAtLeastNWidgets(1));

      final logoutButton = find.widgetWithText(OutlinedButton, 'Log Out');
      expect(logoutButton, findsOneWidget);
      await tester.ensureVisible(logoutButton);
      await tester.tap(logoutButton);
      await tester.pumpAndSettle();

      expect(find.text('Are you sure you want to log out?'), findsOneWidget);
    });
  });
}
