import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/notification_provider.dart';
import 'package:smart_food_waste_donation/providers/volunteer_task_provider.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_dashboard.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_active_task_screen.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_impact_screen.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_claim_screen.dart';
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

Widget _buildTestApp({
  required Widget child,
  UserModel? user,
  VolunteerTaskProvider? volProvider,
  DonationProvider? donProvider,
  String language = 'en',
}) {
  final lp = LocaleProvider();
  lp.setLanguageSyncForTesting(language);

  final auth = AuthProvider();
  final volunteerUser = user ??
      UserModel(
        id: 42,
        name: 'Courier Alex',
        email: 'alex.courier@rescue.org',
        role: 'volunteer',
        phone: '+919876543210',
        vehicleType: 'Bike',
        carryingCapacity: 50,
        reliabilityScore: 98.5,
        isActive: true,
      );
  auth.setCurrentUserForTesting(volunteerUser);

  final vol = volProvider ?? VolunteerTaskProvider();
  final don = donProvider ?? DonationProvider();

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider<DonationProvider>.value(value: don),
      ChangeNotifierProvider<VolunteerTaskProvider>.value(value: vol),
      ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
    ],
    child: MaterialApp(
      theme: AppTheme.lightTheme,
      home: child,
    ),
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  final now = DateTime.now();

  final feasibleTask = DonationModel(
    id: 101,
    donorId: 10,
    foodName: 'Surplus Biryani',
    foodCategory: 'Cooked Meals',
    quantity: 30,
    quantityUnit: 'Meals',
    status: 'accepted',
    pickupAddress: 'Indiranagar, Bangalore (Exact address revealed upon acceptance)',
    createdAt: now.subtract(const Duration(minutes: 50)).toIso8601String(),
    preparationTime: now.subtract(const Duration(minutes: 40)).toIso8601String(),
    expiryTime: now.add(const Duration(hours: 3)).toIso8601String(),
    latitude: 12.97,
    longitude: 77.59,
    ngoName: 'Asha Shelter NGO',
    currentDistanceKm: 2.8,
    currentEtaMinutes: 18,
    remainingMinutes: 140,
    urgencyLevel: 'URGENT',
    pickupMode: 'volunteer_dispatch',
    assignmentId: 201,
  );

  final infeasibleTask = DonationModel(
    id: 102,
    donorId: 11,
    foodName: 'Expired Meals',
    foodCategory: 'Cooked Meals',
    quantity: 20,
    quantityUnit: 'Meals',
    status: 'accepted',
    pickupAddress: 'Whitefield, Bangalore',
    createdAt: now.subtract(const Duration(hours: 7)).toIso8601String(),
    preparationTime: now.subtract(const Duration(hours: 6)).toIso8601String(),
    expiryTime: now.subtract(const Duration(minutes: 10)).toIso8601String(),
    remainingMinutes: 0,
    urgencyLevel: 'WINDOW_ENDED',
    pickupMode: 'volunteer_dispatch',
    feasibilityStatus: 'INFEASIBLE',
  );

  group('Phase 5 Complete Volunteer Role Implementation Tests', () {
    testWidgets('1. Volunteer bottom navigation bar contains exactly 3 tabs (Tasks, Impact, Profile)', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          child: const Scaffold(
            bottomNavigationBar: RoleBottomNav(currentRole: 'volunteer', currentIndex: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(NavigationDestination), findsNWidgets(3));
      expect(find.text('Tasks'), findsOneWidget);
      expect(find.text('Impact'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);
    });

    testWidgets('2. Volunteer dashboard shows Availability toggle in AppBar and elevates active task', (tester) async {
      final volProv = VolunteerTaskProvider();
      final activeTask = feasibleTask.copyWith(
        status: 'volunteer_assigned',
        assignedVolunteerId: 42,
      );
      volProv.setTasksForTesting([activeTask]);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pumpAndSettle();

      // Availability toggle present in AppBar
      expect(find.textContaining('Available'), findsOneWidget);

      // Active task is elevated on the dashboard
      expect(find.text('ACTIVE RESCUES'), findsOneWidget);
      expect(find.text('Surplus Biryani'), findsOneWidget);
      expect(find.text('30 Meals'), findsOneWidget);
      expect(find.text('GO TO PICKUP'), findsOneWidget);
    });

    testWidgets('3. Only feasible tasks are shown to available volunteer; infeasible tasks are hidden', (tester) async {
      final volProv = VolunteerTaskProvider();
      volProv.setTasksForTesting([feasibleTask, infeasibleTask]);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pumpAndSettle();

      // Feasible task is displayed
      expect(find.text('Surplus Biryani'), findsOneWidget);
      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
      expect(find.text('PASS'), findsOneWidget);

      // Infeasible task is completely hidden
      expect(find.text('Expired Meals'), findsNothing);
    });

    testWidgets('4. Task card shows logistics details and approximate area before acceptance', (tester) async {
      final volProv = VolunteerTaskProvider();
      volProv.setTasksForTesting([feasibleTask]);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pumpAndSettle();

      // Approximate pickup area before acceptance
      expect(find.textContaining('Exact address revealed upon acceptance'), findsOneWidget);
      // Dropoff NGO area
      expect(find.text('Asha Shelter NGO'), findsOneWidget);
      // Distance and mission time
      expect(find.text('2.8 km'), findsOneWidget);
      expect(find.textContaining('18 min'), findsOneWidget);
    });

    testWidgets('5. Public Claim Link screen presents preview without exposing OTP or private donor info', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          child: const VolunteerClaimScreen(token: 'CLAIM-TOKEN-12345'),
        ),
      );
      await tester.pump();

      // Screen loads preview scaffold
      expect(find.byType(VolunteerClaimScreen), findsOneWidget);
      // Never exposes OTP in claim link preview
      expect(find.text('123456'), findsNothing);
      expect(find.textContaining('OTP'), findsNothing);
    });

    testWidgets('6. Assignment ID correctness: cached and never uses ID 0', (tester) async {
      final volProv = VolunteerTaskProvider();
      volProv.setAssignmentIdForTesting(101, 201);

      expect(volProv.getAssignmentId(101), equals(201));
      expect(volProv.getAssignmentId(101), isNot(equals(0)));

      // Setting ID 0 is strictly rejected
      volProv.setAssignmentIdForTesting(999, 0);
      expect(volProv.getAssignmentId(999), isNull);
    });

    testWidgets('7. 7-Step Courier Workflow: Accepted -> Start Pickup -> Arrived -> Fallback -> Transit -> NGO -> Deliver', (tester) async {
      final volProv = VolunteerTaskProvider();
      final donProv = DonationProvider();

      final activeDonation = feasibleTask.copyWith(
        status: 'accepted',
        assignmentId: 201,
        donorName: 'Chef Ramesh',
        donorPhone: '+91 98765 00000',
        pickupAddress: '12/4, 100ft Road, Indiranagar, Bangalore',
      );
      volProv.setAssignmentIdForTesting(101, 201);
      volProv.setActiveTaskForTesting(activeDonation);
      donProv.setCurrentDetailForTesting(activeDonation);

      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          donProvider: donProv,
          child: const VolunteerActiveTaskScreen(donationId: 101),
        ),
      );
      await tester.pumpAndSettle();

      // Stage 0: GO TO PICKUP button present
      expect(find.text('GO TO PICKUP'), findsOneWidget);
      expect(find.textContaining('Food Safety: Verify covered packaging'), findsOneWidget);

      // Tap GO TO PICKUP -> Stage 1: On the way
      await tester.runAsync(() async {
        await tester.tap(find.text('GO TO PICKUP'));
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      expect(find.text('ARRIVED'), findsOneWidget);
      expect(find.textContaining("GPS Inaccurate? Confirm Arrival with \"I'm Here\""), findsOneWidget);

      // Fallback arrival confirmed
      await tester.runAsync(() async {
        await tester.tap(find.textContaining("GPS Inaccurate? Confirm Arrival with \"I'm Here\""));
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      // Stage 2: Arrived at Donor -> VERIFY OTP
      expect(find.text('VERIFY OTP'), findsOneWidget);
      await tester.tap(find.text('VERIFY OTP'));
      await tester.pumpAndSettle();

      // Enter OTP via custom keypad
      expect(find.text('ENTER PICKUP CODE'), findsOneWidget);
      await tester.runAsync(() async {
        for (final digit in ['1', '2', '3', '4', '5', '6']) {
          await tester.tap(find.widgetWithText(OutlinedButton, digit));
          await Future.delayed(const Duration(milliseconds: 50));
        }
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      // Stage 3: Food Collected -> START TRANSIT
      expect(find.text('GO TO NGO / START TRANSIT'), findsOneWidget);
      await tester.runAsync(() async {
        await tester.tap(find.text('GO TO NGO / START TRANSIT'));
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      // Stage 4: In Transit -> ARRIVED AT NGO
      expect(find.text('ARRIVED AT NGO'), findsOneWidget);
      await tester.runAsync(() async {
        await tester.tap(find.text('ARRIVED AT NGO'));
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      // Stage 5: Confirm Delivery
      expect(find.text('DELIVER'), findsOneWidget);
      await tester.runAsync(() async {
        await tester.tap(find.text('DELIVER'));
        await Future.delayed(const Duration(milliseconds: 100));
      });
      await tester.pumpAndSettle();

      // Stage 6: Delivered / Completed
      expect(find.textContaining('Completed'), findsWidgets);
    });

    testWidgets('8. Report Problem dialog presents 9 canonical reasons', (tester) async {
      final volProv = VolunteerTaskProvider();
      final donProv = DonationProvider();

      final activeDonation = feasibleTask.copyWith(
        status: 'en_route',
        assignmentId: 201,
      );
      volProv.setActiveTaskForTesting(activeDonation);
      donProv.setCurrentDetailForTesting(activeDonation);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          donProvider: donProv,
          child: const VolunteerActiveTaskScreen(donationId: 101),
        ),
      );
      await tester.pumpAndSettle();

      // Tap report problem icon in AppBar
      await tester.tap(find.byIcon(Icons.report_problem_outlined).first);
      await tester.pumpAndSettle();

      expect(find.text('Cannot find donor'), findsOneWidget);
      expect(find.text('Donor unavailable'), findsOneWidget);
      expect(find.text('Vehicle problem'), findsOneWidget);
      expect(find.text('Road blocked'), findsOneWidget);
      expect(find.text('Food condition issue'), findsOneWidget);
      expect(find.text('Wrong quantity'), findsOneWidget);
      expect(find.text('Cannot locate NGO'), findsOneWidget);
      expect(find.text('Safety concern'), findsOneWidget);
      expect(find.text('Other'), findsOneWidget);
    });

    testWidgets('9. Impact Screen shows pickups, meals moved, success rate, reliability tier, and estimated CO2', (tester) async {
      final volProv = VolunteerTaskProvider();
      final completedTask = feasibleTask.copyWith(
        status: 'delivered',
        quantity: 45,
      );
      volProv.setTasksForTesting([completedTask]);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerImpactScreen(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Volunteer Courier Impact'), findsOneWidget);
      expect(find.text('Completed Pickups'), findsOneWidget);
      expect(find.text('Meals Rescued'), findsOneWidget);
      expect(find.text('45'), findsOneWidget);
      expect(find.text('Reliability Tier'), findsOneWidget);
      expect(find.text('Champion Courier (Tier 1)'), findsOneWidget);
      expect(find.textContaining('CO₂ Emission Prevented*'), findsOneWidget);
      expect(find.textContaining('Environmental CO₂ emissions prevented are estimates'), findsOneWidget);
    });

    testWidgets('10. Profile Screen shows courier identity, phone, vehicle, capacity, language, and logout', (tester) async {
      final volUser = UserModel(
        id: 42,
        name: 'Courier Alex',
        email: 'alex.courier@rescue.org',
        role: 'volunteer',
        phone: '+91 98765 43210',
        vehicleType: 'Bike',
        carryingCapacity: 50,
        reliabilityScore: 98.5,
        isActive: true,
      );

      await tester.pumpWidget(
        _buildTestApp(
          user: volUser,
          child: const ProfileScreen(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Courier Alex'), findsOneWidget);
      expect(find.text('+91 98765 43210'), findsOneWidget);
      expect(find.text('BIKE'), findsWidgets);
      expect(find.text('50 Meals'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);
    });

    testWidgets('11. Volunteer strings are properly localized across English, Tamil, and Hindi', (tester) async {
      final lp = LocaleProvider();

      // English
      lp.setLanguageSyncForTesting('en');
      expect(lp.translate('nav_tasks'), equals('Tasks'));
      expect(lp.translate('action_go_to_pickup'), equals('GO TO PICKUP'));
      expect(lp.translate('action_arrived'), equals('ARRIVED'));
      expect(lp.translate('action_verify_otp'), equals('VERIFY OTP'));
      expect(lp.translate('action_deliver'), equals('DELIVER'));

      // Tamil
      lp.setLanguageSyncForTesting('ta');
      expect(lp.translate('nav_tasks'), equals('பணிகள்'));
      expect(lp.translate('action_go_to_pickup'), equals('பிக்கப் செய்ய செல்லவும்'));
      expect(lp.translate('action_arrived'), equals('வந்து சேர்ந்தேன்'));
      expect(lp.translate('action_verify_otp'), equals('OTP சரிபார்க்கவும்'));
      expect(lp.translate('action_deliver'), equals('டெலிவரி செய்'));

      // Hindi
      lp.setLanguageSyncForTesting('hi');
      expect(lp.translate('nav_tasks'), equals('कार्य'));
      expect(lp.translate('action_go_to_pickup'), equals('पिकअप के लिए जाएं'));
      expect(lp.translate('action_arrived'), equals('पहुंच गए'));
      expect(lp.translate('action_verify_otp'), equals('OTP सत्यापित करें'));
      expect(lp.translate('action_deliver'), equals('डिलीवर करें'));
    });
  });
}
