import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
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
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

class MockVolunteerTaskProvider extends VolunteerTaskProvider {
  bool networkCalled = false;

  @override
  Future<void> fetchMyTasks() async {
    networkCalled = true;
    // Don't call live network in widget tests
  }

  @override
  Future<DonationModel?> fetchTaskDetail(int donationId) async {
    return activeTask;
  }

  @override
  Future<void> setAvailability(bool available) async {
    setAvailabilityForTesting(available);
  }

  @override
  Future<bool> startPickup(int donationId, {int? assignmentId}) async {
    if (activeTask != null) {
      setActiveTaskForTesting(activeTask!.copyWith(status: 'en_route'));
    }
    return true;
  }

  @override
  Future<bool> markArrived(int donationId, {int? assignmentId, String method = 'gps', String? reason}) async {
    if (activeTask != null) {
      setActiveTaskForTesting(activeTask!.copyWith(status: 'arrived'));
    }
    return true;
  }

  @override
  Future<bool> verifyPickupOtp(int donationId, String enteredOtp) async {
    if (enteredOtp == '123456') {
      if (activeTask != null) {
        setActiveTaskForTesting(activeTask!.copyWith(status: 'collected'));
      }
      return true;
    }
    return false;
  }

  @override
  Future<bool> startTransit(int donationId, {int? assignmentId}) async {
    if (activeTask != null) {
      setActiveTaskForTesting(activeTask!.copyWith(status: 'in_transit'));
    }
    return true;
  }

  @override
  Future<bool> markDelivered(int donationId, {int? assignmentId}) async {
    if (activeTask != null) {
      setActiveTaskForTesting(activeTask!.copyWith(status: 'delivered'));
    }
    return true;
  }
}

class MockDonationProvider extends DonationProvider {
  @override
  Future<void> fetchDonations({String? status, String? category, bool myDonationsOnly = false}) async {
    // Avoid real network in test
  }

  @override
  Future<DonationModel?> fetchDonationDetail(int donationId) async {
    return currentDetail;
  }

  @override
  Future<Map<String, dynamic>?> updateVolunteerLocation({
    required double latitude,
    required double longitude,
    int? donationId,
    int? assignmentId,
    double? speedKmh,
    double? heading,
    double? batteryLevel,
  }) async {
    return {'success': true};
  }
}

Widget _buildTestApp({
  required Widget child,
  UserModel? user,
  MockVolunteerTaskProvider? volProvider,
  MockDonationProvider? donationProvider,
}) {
  final auth = AuthProvider();
  final volunteerUser = user ??
      UserModel(
        id: 42,
        name: 'Courier Jamie',
        email: 'jamie.courier@rescue.org',
        role: 'volunteer',
        phone: '+919876543210',
        vehicleType: 'Bike',
        carryingCapacity: 60,
        reliabilityScore: 98.5,
        isActive: true,
      );
  auth.setCurrentUserForTesting(volunteerUser);

  final vol = volProvider ?? MockVolunteerTaskProvider();
  final don = donationProvider ?? MockDonationProvider();

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
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
  TestWidgetsFlutterBinding.ensureInitialized();

  final feasibleTask = DonationModel(
    id: 101,
    donorId: 10,
    foodName: 'Hot Veg Biryani',
    quantity: 25.0,
    quantityUnit: 'Meals',
    status: 'accepted',
    pickupAddress: 'Indiranagar (Exact address revealed upon acceptance)',
    preparationTime: DateTime.now().subtract(const Duration(minutes: 30)).toIso8601String(),
    expiryTime: DateTime.now().add(const Duration(hours: 3)).toIso8601String(),
    foodCategory: 'Cooked Meals',
    createdAt: DateTime.now().toIso8601String(),
    feasibility: RescueFeasibilityModel(
      feasibilityStatus: 'FEASIBLE',
      feasibilityLabel: 'Feasible',
      isFeasible: true,
      estimatedPickupMinutes: 10,
      estimatedTravelMinutes: 15,
      remainingBufferMinutes: 95,
      explanation: 'Sufficient rescue window margin',
    ),
    urgencyLevel: 'MEDIUM',
    pickupMode: 'volunteer_dispatch',
    assignmentId: 201,
  );

  final infeasibleTask = DonationModel(
    id: 102,
    donorId: 11,
    foodName: 'Expired Curry Meals',
    quantity: 15.0,
    quantityUnit: 'Meals',
    status: 'accepted',
    pickupAddress: 'Whitefield',
    preparationTime: DateTime.now().subtract(const Duration(hours: 6)).toIso8601String(),
    expiryTime: DateTime.now().subtract(const Duration(minutes: 10)).toIso8601String(),
    foodCategory: 'Cooked Meals',
    createdAt: DateTime.now().toIso8601String(),
    feasibility: RescueFeasibilityModel(
      feasibilityStatus: 'INFEASIBLE',
      feasibilityLabel: 'Infeasible',
      isFeasible: false,
      estimatedPickupMinutes: 40,
      estimatedTravelMinutes: 45,
      remainingBufferMinutes: -95,
      explanation: 'Window expired before mission could complete',
    ),
    urgencyLevel: 'CRITICAL',
    pickupMode: 'volunteer_dispatch',
  );

  group('SMART FOOD RESCUE PLATFORM — VOLUNTEER ROLE COMPLETE INTEGRATION SUITE', () {
    testWidgets('1. Navigation & 3-Tab Architecture: exactly Tasks, Impact, and Profile', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          child: const Scaffold(
            body: Center(child: Text('Volunteer View')),
            bottomNavigationBar: RoleBottomNav(currentRole: 'volunteer', currentIndex: 0),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 300));

      // Exactly 3 tabs
      expect(find.text('Tasks'), findsOneWidget);
      expect(find.text('Impact'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);
      // Ensure NO Availability tab was created
      expect(find.text('Availability'), findsNothing);
    });

    testWidgets('2. Volunteer Dashboard: Feasible-only filtering & pre-assignment address masking', (tester) async {
      final volProv = MockVolunteerTaskProvider();
      volProv.setTasksForTesting([feasibleTask, infeasibleTask]);
      volProv.setAvailabilityForTesting(true);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // Feasible task is displayed
      expect(find.text('Hot Veg Biryani'), findsOneWidget);
      // Infeasible task is NEVER displayed to the volunteer
      expect(find.text('Expired Curry Meals'), findsNothing);

      // Pre-assignment exact address privacy: masked notice shown
      expect(find.textContaining('Exact address revealed upon acceptance'), findsOneWidget);

      // Primary action button is ACCEPT RESCUE
      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
    });

    testWidgets('3. Volunteer Dashboard: Availability toggle & Offline banner', (tester) async {
      final volProv = MockVolunteerTaskProvider();
      volProv.setTasksForTesting([feasibleTask]);
      volProv.setAvailabilityForTesting(false); // Courier is unavailable / offline

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // When unavailable: displays Offline notice banner
      expect(find.textContaining('You are currently marked as Unavailable'), findsOneWidget);
      expect(find.textContaining('app bar to receive new rescue tasks'), findsOneWidget);
    });

    testWidgets('4. Active Task Elevation on Dashboard', (tester) async {
      final volProv = MockVolunteerTaskProvider();
      final activeDonation = feasibleTask.copyWith(
        status: 'volunteer_assigned',
        foodName: 'Urgent Sambar Meals',
      );
      volProv.setTasksForTesting([activeDonation]);
      volProv.setActiveTaskForTesting(activeDonation);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerDashboardScreen(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // Elevated Active Task header card
      expect(find.text('ACTIVE RESCUES'), findsOneWidget);
      expect(find.text('Urgent Sambar Meals'), findsOneWidget);
      expect(find.text('GO TO PICKUP'), findsOneWidget);
    });

    testWidgets('5. 7-Step Courier Workflow: Accepted -> Start Pickup -> Arrived -> Fallback -> Transit -> NGO -> Deliver', (tester) async {
      tester.view.physicalSize = const Size(800, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final volProv = MockVolunteerTaskProvider();
      final donProv = MockDonationProvider();

      final activeDonation = DonationModel(
        id: 101,
        donorId: 10,
        foodName: 'Hot Veg Biryani',
        foodCategory: 'Cooked Meals',
        quantity: 25.0,
        quantityUnit: 'Meals',
        status: 'volunteer_assigned',
        pickupAddress: '45 MG Road, Indiranagar, Bangalore',
        preparationTime: DateTime.now().subtract(const Duration(minutes: 30)).toIso8601String(),
        expiryTime: DateTime.now().add(const Duration(hours: 3)).toIso8601String(),
        createdAt: DateTime.now().toIso8601String(),
        feasibility: RescueFeasibilityModel(
          feasibilityStatus: 'FEASIBLE',
          feasibilityLabel: 'Feasible',
          isFeasible: true,
          estimatedPickupMinutes: 10,
          estimatedTravelMinutes: 15,
          remainingBufferMinutes: 95,
          explanation: 'Sufficient rescue window margin',
        ),
        urgencyLevel: 'MEDIUM',
        pickupMode: 'volunteer_dispatch',
        assignmentId: 501,
      );

      volProv.setActiveTaskForTesting(activeDonation);
      volProv.setAssignmentIdForTesting(101, 501);
      donProv.setCurrentDetailForTesting(activeDonation);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          donationProvider: donProv,
          child: const VolunteerActiveTaskScreen(donationId: 101),
        ),
      );
      await tester.pumpAndSettle();

      // Stage 0: GO TO PICKUP button present
      expect(find.text('GO TO PICKUP'), findsOneWidget);
      expect(find.textContaining('Food Safety: Verify covered packaging'), findsOneWidget);

      // Tap GO TO PICKUP
      await tester.tap(find.text('GO TO PICKUP'));
      await tester.pumpAndSettle();

      // Stage 1: On the way -> shows ARRIVED
      expect(find.text('ARRIVED'), findsOneWidget);
      // Fallback arrival option is visible (Section 14)
      expect(find.textContaining("GPS Inaccurate? Confirm Arrival with \"I'm Here\""), findsOneWidget);

      // Tap ARRIVED
      await tester.tap(find.text('ARRIVED'));
      await tester.pumpAndSettle();

      // Stage 2: Arrived at Donor -> VERIFY OTP (Section 15)
      expect(find.text('VERIFY OTP'), findsOneWidget);
      await tester.tap(find.text('VERIFY OTP'));
      await tester.pumpAndSettle();

      // Enter OTP via custom one-handed keypad
      expect(find.text('ENTER PICKUP CODE'), findsOneWidget);
      for (final digit in ['1', '2', '3', '4', '5', '6']) {
        await tester.tap(find.widgetWithText(OutlinedButton, digit));
        await tester.pump(const Duration(milliseconds: 50));
      }
      await tester.pumpAndSettle();

      // Stage 3: Food Collected -> Prompt GO TO NGO / START TRANSIT (Section 18)
      expect(find.text('GO TO NGO / START TRANSIT'), findsOneWidget);
      await tester.tap(find.text('GO TO NGO / START TRANSIT'));
      await tester.pump(const Duration(milliseconds: 300));

      // Stage 4: In Transit -> ARRIVED AT NGO (Section 19)
      expect(find.text('ARRIVED AT NGO'), findsOneWidget);
      await tester.tap(find.text('ARRIVED AT NGO'));
      await tester.pump(const Duration(milliseconds: 300));

      // Stage 5: Confirm Delivery (Section 19)
      expect(find.text('DELIVER'), findsOneWidget);
      await tester.tap(find.text('DELIVER'));
      await tester.pump(const Duration(milliseconds: 300));

      // Stage 6: Delivered / Completed
      expect(find.text('Rescue Completed 🎉'), findsOneWidget);
    });

    testWidgets('6. Report Problem modal accessible with all 9 canonical reasons', (tester) async {
      final volProv = MockVolunteerTaskProvider();
      final donProv = MockDonationProvider();

      final activeDonation = feasibleTask.copyWith(
        status: 'en_route',
        assignmentId: 201,
      );
      volProv.setActiveTaskForTesting(activeDonation);
      volProv.setAssignmentIdForTesting(101, 201);
      donProv.setCurrentDetailForTesting(activeDonation);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          donationProvider: donProv,
          child: const VolunteerActiveTaskScreen(donationId: 101),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // Tap Report Problem IconButton
      final reportBtn = find.byIcon(Icons.report_problem_outlined);
      expect(reportBtn, findsOneWidget);
      await tester.tap(reportBtn);
      await tester.pump(const Duration(milliseconds: 300));

      // Verify Modal opens with canonical reasons (Section 24)
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

    testWidgets('7. Impact Screen: Pickups, Meals, Success Rate, Reliability Tier, Estimated CO2', (tester) async {
      final volProv = MockVolunteerTaskProvider();
      final deliveredTask = feasibleTask.copyWith(
        status: 'delivered',
        quantity: 50.0,
      );
      volProv.setTasksForTesting([deliveredTask]);

      await tester.pumpWidget(
        _buildTestApp(
          volProvider: volProv,
          child: const VolunteerImpactScreen(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // Header and real metrics
      expect(find.text('Volunteer Courier Impact'), findsOneWidget);
      expect(find.text('Completed Pickups'), findsOneWidget);
      expect(find.text('Meals Rescued'), findsOneWidget);
      expect(find.text('On-Time Delivery Rate'), findsOneWidget);

      // Reliability Tier Badge (Section 25)
      expect(find.text('Champion Courier (Tier 1)'), findsOneWidget);

      // Environmental figures marked as Estimated (Section 25)
      expect(find.textContaining('*Environmental CO₂ emissions prevented are estimates'), findsOneWidget);
    });

    testWidgets('8. Profile Screen: Courier attributes & Logout', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          child: const ProfileScreen(),
        ),
      );
      await tester.pump(const Duration(milliseconds: 500));

      // User details
      expect(find.text('Courier Jamie'), findsOneWidget);
      expect(find.text('jamie.courier@rescue.org'), findsOneWidget);
      expect(find.text('Volunteer Hero'), findsOneWidget);
      // Logout button present
      expect(find.text('Log Out'), findsOneWidget);
    });
  });
}
