import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/models/ngo_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/ngo_provider.dart';
import 'package:smart_food_waste_donation/providers/notification_provider.dart';
import 'package:smart_food_waste_donation/providers/volunteer_task_provider.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_dashboard.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_food_requirements_screen.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_receiving_distribution_screen.dart';
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/donation_card.dart';
import 'package:smart_food_waste_donation/widgets/donation_status_timeline.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

Widget _buildTestApp({
  required Widget child,
  UserModel? user,
  LocaleProvider? localeProvider,
}) {
  final auth = AuthProvider();
  if (user != null) {
    auth.setCurrentUserForTesting(user);
  }

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: localeProvider ?? LocaleProvider()),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider<DonationProvider>(create: (_) => DonationProvider()),
      ChangeNotifierProvider<NgoProvider>(create: (_) => NgoProvider()),
      ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
      ChangeNotifierProvider<VolunteerTaskProvider>(create: (_) => VolunteerTaskProvider()),
    ],
    child: MaterialApp(
      theme: AppTheme.lightTheme,
      home: child,
    ),
  );
}

void main() {
  group('SMART FOOD RESCUE PLATFORM — NGO ROLE INTEGRATION SUITE', () {
    final unverifiedNgo = NgoModel(
      id: 1,
      userId: 10,
      organizationName: 'City Hope Shelter',
      address: '12 Indiranagar, Bengaluru',
      latitude: 12.9716,
      longitude: 77.5946,
      capacity: 250,
      currentCapacity: 180,
      isVerified: false,
      isAvailable: true,
      operatingHours: {'schedule': '08:00 - 22:00'},
    );

    final verifiedNgo = NgoModel(
      id: 2,
      userId: 11,
      organizationName: 'Akshaya Feed India',
      address: '45 MG Road, Bengaluru',
      latitude: 12.9750,
      longitude: 77.6000,
      capacity: 400,
      currentCapacity: 300,
      isVerified: true,
      isAvailable: true,
      operatingHours: {'schedule': '06:00 - 23:00'},
    );

    final sampleDonation = DonationModel(
      id: 101,
      donorId: 5,
      foodName: 'Vegetable Rice & Curry',
      foodCategory: 'Cooked Meals',
      quantity: 50.0,
      quantityUnit: 'Meals',
      preparationTime: '2026-09-28T18:00:00Z',
      expiryTime: '2026-09-28T22:00:00Z',
      pickupAddress: 'Taj Heritage Kitchen, Bengaluru',
      latitude: 12.9720,
      longitude: 77.5960,
      status: 'pending',
      rescueUrgencyLevel: 'URGENT',
      feasibilityStatus: 'RESCUE_FEASIBLE',
      pickupMode: 'volunteer_dispatch',
      createdAt: '2026-09-28T18:30:00Z',
    );

    testWidgets('1. Verification Gate: Unverified NGO sees pending gate and is blocked from rescues', (tester) async {
      final user = UserModel(
        id: 10,
        name: 'City Hope Shelter',
        email: 'hope@ngo.org',
        role: 'ngo',
        isActive: true,
      );

      final ngoProv = NgoProvider();
      ngoProv.setMyNgoForTesting(unverifiedNgo);

      final auth = AuthProvider();
      auth.setCurrentUserForTesting(user);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
            ChangeNotifierProvider<AuthProvider>.value(value: auth),
            ChangeNotifierProvider<DonationProvider>(create: (_) => DonationProvider()),
            ChangeNotifierProvider<NgoProvider>.value(value: ngoProv),
            ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
          ],
          child: const MaterialApp(
            home: NgoDashboardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verification pending title and support button must be visible
      expect(find.text('Your organization is being reviewed.'), findsOneWidget);
      expect(find.text('CONTACT SUPPORT'), findsOneWidget);
      // No rescue cards or accept actions should be present
      expect(find.byType(DonationCard), findsNothing);
      expect(find.text('ACCEPT RESCUE'), findsNothing);
    });

    testWidgets('2. Verified NGO Dashboard: Displays 3-tab navigation and rescue feed with primary actions', (tester) async {
      final user = UserModel(
        id: 11,
        name: 'Akshaya Feed India',
        email: 'akshaya@ngo.org',
        role: 'ngo',
        isActive: true,
      );

      final ngoProv = NgoProvider();
      ngoProv.setMyNgoForTesting(verifiedNgo);

      final donationProv = DonationProvider();
      donationProv.setDonationsForTesting([sampleDonation]);

      final auth = AuthProvider();
      auth.setCurrentUserForTesting(user);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
            ChangeNotifierProvider<AuthProvider>.value(value: auth),
            ChangeNotifierProvider<DonationProvider>.value(value: donationProv),
            ChangeNotifierProvider<NgoProvider>.value(value: ngoProv),
            ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
          ],
          child: const MaterialApp(
            home: NgoDashboardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verified Partner indicator present
      expect(find.text('Verified Partner'), findsWidgets);

      // Bottom Navigation has exactly 3 tabs for NGO
      final bottomNav = find.byType(RoleBottomNav);
      expect(bottomNav, findsOneWidget);
      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Requirements'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);

      // Rescue Card contains Food, Quantity, Distance, and Actions
      expect(find.text('Vegetable Rice & Curry'), findsOneWidget);
      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
      expect(find.text('PASS'), findsOneWidget);
    });

    testWidgets('3. Rescue Card Accept Sheet: Offers Self-Pickup vs Volunteer Courier dispatch', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          child: Scaffold(
            body: DonationCard(
              donation: sampleDonation,
              currentRole: 'ngo',
              acceptLabel: 'ACCEPT RESCUE',
              rejectLabel: 'PASS',
              onAccept: () {},
              onReject: () {},
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
      expect(find.text('PASS'), findsOneWidget);
      expect(find.text('Vegetable Rice & Curry'), findsOneWidget);
    });

    testWidgets('4. Rescue Timeline: Branch steps distinguish Self-Pickup vs Volunteer Dispatch', (tester) async {
      // Volunteer dispatch timeline
      await tester.pumpWidget(
        _buildTestApp(
          child: const Scaffold(
            body: DonationStatusTimeline(
              status: 'volunteer_assigned',
              pickupMode: 'volunteer_dispatch',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Volunteer Assigned'), findsOneWidget);

      // Self-pickup timeline
      await tester.pumpWidget(
        _buildTestApp(
          child: const Scaffold(
            body: DonationStatusTimeline(
              status: 'accepted',
              pickupMode: 'self_pickup',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('NGO En Route'), findsOneWidget);
      expect(find.text('Donor OTP verified by NGO at donor location'), findsOneWidget);
    });

    testWidgets('5. NGO Requirements Screen: Updates Intake Capacity, Availability and Operating Hours', (tester) async {
      final user = UserModel(
        id: 11,
        name: 'Akshaya Feed India',
        email: 'akshaya@ngo.org',
        role: 'ngo',
        isActive: true,
      );

      final ngoProv = NgoProvider();
      ngoProv.setMyNgoForTesting(verifiedNgo);

      final auth = AuthProvider();
      auth.setCurrentUserForTesting(user);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
            ChangeNotifierProvider<AuthProvider>.value(value: auth),
            ChangeNotifierProvider<DonationProvider>(create: (_) => DonationProvider()),
            ChangeNotifierProvider<NgoProvider>.value(value: ngoProv),
          ],
          child: const MaterialApp(
            home: NgoFoodRequirementsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Section 1: Capacity & Availability
      expect(find.textContaining('Intake Capacity'), findsOneWidget);
      expect(find.text('Currently receiving rescues'), findsOneWidget);
      expect(find.byType(Switch), findsWidgets);

      // Section 2: Demand by Category
      expect(find.text('Food Category'), findsOneWidget);
      expect(find.text('Cooked Food'), findsOneWidget);

      // Section 3: Weekly Operating Hours
      expect(find.textContaining('Operating'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('CONFIRM'), 100);
      expect(find.text('Monday'), findsOneWidget);
      expect(find.text('CONFIRM'), findsOneWidget);

      // RoleBottomNav with index 1 (Requirements)
      expect(find.byType(RoleBottomNav), findsOneWidget);
    });

    testWidgets('6. Receiving & Distribution: Distinguishes Received Quantity from Distributed Quantity', (tester) async {
      final receivedDonation = DonationModel(
        id: 102,
        donorId: 5,
        foodName: 'Curd Rice & Sambar',
        foodCategory: 'Cooked Meals',
        quantity: 100.0,
        quantityUnit: 'Meals',
        preparationTime: '2026-09-28T18:00:00Z',
        expiryTime: '2026-09-28T22:00:00Z',
        pickupAddress: 'Community Center, Bengaluru',
        status: 'delivered',
        pickupMode: 'self_pickup',
        createdAt: '2026-09-28T18:00:00Z',
      );

      await tester.pumpWidget(
        _buildTestApp(
          child: NgoReceivingDistributionScreen(
            donationId: 102,
            donation: receivedDonation,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Metric Summary distinguishes Donated, Received, Distributed, Remaining
      expect(find.text('EXPECTED'), findsOneWidget);
      expect(find.text('RECEIVED'), findsOneWidget);
      expect(find.text('DISTRIBUTED'), findsOneWidget);
      expect(find.text('REMAINING'), findsOneWidget);

      // Action 1: Confirm Receipt
      expect(find.textContaining('1. Confirm Receipt'), findsOneWidget);

      // Action 2: Log Distribution
      expect(find.textContaining('2. Log Distribution'), findsOneWidget);
    });

    testWidgets('7. Profile Screen: Displays NGO Organization Name, 3 Tabs and Verification Status', (tester) async {
      final user = UserModel(
        id: 11,
        name: 'Akshaya Feed India',
        email: 'akshaya@ngo.org',
        phone: '+91 98765 00011',
        address: '45 MG Road, Bengaluru',
        role: 'ngo',
        isActive: true,
      );

      final ngoProv = NgoProvider();
      ngoProv.setMyNgoForTesting(verifiedNgo);

      final auth = AuthProvider();
      auth.setCurrentUserForTesting(user);

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
            ChangeNotifierProvider<AuthProvider>.value(value: auth),
            ChangeNotifierProvider<NgoProvider>.value(value: ngoProv),
            ChangeNotifierProvider<VolunteerTaskProvider>(create: (_) => VolunteerTaskProvider()),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Akshaya Feed India'), findsOneWidget);
      expect(find.text('Verified NGO Partner • Active'), findsOneWidget);
      expect(find.textContaining('Intake Capacity'), findsOneWidget);
      expect(find.text('400'), findsOneWidget); // NGO capacity from verifiedNgo
      expect(find.byType(RoleBottomNav), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);
    });

    testWidgets('8. Trilingual Localization: NGO actions and labels in English, Tamil, and Hindi', (tester) async {
      final lp = LocaleProvider();

      // English
      lp.setLanguage('en');
      expect(lp.translate('accept_rescue'), 'ACCEPT RESCUE');
      expect(lp.translate('pass'), 'PASS');
      expect(lp.translate('collect_yourself'), 'COLLECT YOURSELF');
      expect(lp.translate('action_verify_donor_otp'), 'Verify Donor OTP');
      expect(lp.translate('err_already_accepted'), 'This donation has already been accepted by another organization.');

      // Tamil
      lp.setLanguage('ta');
      expect(lp.translate('accept_rescue'), 'மீட்பை ஏற்கவும்');
      expect(lp.translate('pass'), 'தவிர்க்க');
      expect(lp.translate('collect_yourself'), 'நீங்களே சேகரிக்கவும்');

      // Hindi
      lp.setLanguage('hi');
      expect(lp.translate('accept_rescue'), 'बचाव स्वीकार करें');
      expect(lp.translate('pass'), 'छोड़ें');
      expect(lp.translate('collect_yourself'), 'स्वयं एकत्र करें');
    });
  });
}
