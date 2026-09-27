import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/providers/admin_provider.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/ngo_provider.dart';
import 'package:smart_food_waste_donation/providers/volunteer_provider.dart';
import 'package:smart_food_waste_donation/providers/volunteer_task_provider.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_audit_log_screen.dart';
import 'package:smart_food_waste_donation/screens/auth/forgot_password_screen.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_receiving_distribution_screen.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_task_history_screen.dart';
import 'package:smart_food_waste_donation/screens/volunteer/volunteer_vehicle_profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/availability_toggle.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

Widget wrapWithProviders(Widget child, {
  AuthProvider? authProvider,
  VolunteerTaskProvider? volunteerTaskProvider,
  VolunteerProvider? volunteerProvider,
  NgoProvider? ngoProvider,
  AdminProvider? adminProvider,
  DonationProvider? donationProvider,
}) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
      ChangeNotifierProvider<AuthProvider>.value(value: authProvider ?? AuthProvider()),
      ChangeNotifierProvider<VolunteerTaskProvider>.value(value: volunteerTaskProvider ?? VolunteerTaskProvider()),
      ChangeNotifierProvider<VolunteerProvider>.value(value: volunteerProvider ?? VolunteerProvider()),
      ChangeNotifierProvider<NgoProvider>.value(value: ngoProvider ?? NgoProvider()),
      ChangeNotifierProvider<AdminProvider>.value(value: adminProvider ?? AdminProvider()),
      ChangeNotifierProvider<DonationProvider>.value(value: donationProvider ?? DonationProvider()),
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

  group('Authoritative Master Prompt Navigation & Screen Inventory Tests', () {

    testWidgets('1. RoleBottomNav enforces exact role tab counts and destinations', (tester) async {
      // DONOR: exactly 4 tabs
      await tester.pumpWidget(wrapWithProviders(
        const Scaffold(bottomNavigationBar: RoleBottomNav(currentRole: 'donor', currentIndex: 0)),
      ));
      expect(find.byType(NavigationDestination), findsNWidgets(4));

      // NGO: exactly 3 tabs
      await tester.pumpWidget(wrapWithProviders(
        const Scaffold(bottomNavigationBar: RoleBottomNav(currentRole: 'ngo', currentIndex: 0)),
      ));
      expect(find.byType(NavigationDestination), findsNWidgets(3));

      // VOLUNTEER: exactly 3 tabs
      await tester.pumpWidget(wrapWithProviders(
        const Scaffold(bottomNavigationBar: RoleBottomNav(currentRole: 'volunteer', currentIndex: 0)),
      ));
      expect(find.byType(NavigationDestination), findsNWidgets(3));

      // ADMIN: exactly 5 destinations
      await tester.pumpWidget(wrapWithProviders(
        const Scaffold(bottomNavigationBar: RoleBottomNav(currentRole: 'admin', currentIndex: 0)),
      ));
      expect(find.byType(NavigationDestination), findsNWidgets(5));
    });

    testWidgets('2. ForgotPasswordScreen renders validation and dispatch', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(wrapWithProviders(const ForgotPasswordScreen()));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);

      // Tap submit with empty field -> shows error
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();
      expect(find.text('This field is required'), findsOneWidget);

      // Enter valid email and submit -> shows confirmation
      await tester.enterText(find.byType(TextFormField), 'donor@test.org');
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      expect(find.text('Instructions Sent'), findsOneWidget);
    });

    testWidgets('3. VolunteerVehicleProfileScreen (V5) allows selecting transport mode and capacity', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final volProv = VolunteerProvider();
      await tester.pumpWidget(wrapWithProviders(
        const VolunteerVehicleProfileScreen(),
        volunteerProvider: volProv,
      ));
      await tester.pumpAndSettle();

      expect(find.widgetWithText(AppBar, 'Vehicle Profile'), findsOneWidget);
      expect(find.text('Walking'), findsOneWidget);
      expect(find.text('Bike'), findsOneWidget);
      expect(find.text('Car'), findsOneWidget);
      expect(find.text('Van'), findsOneWidget);

      // Select 'Car'
      await tester.tap(find.text('Car'));
      await tester.pumpAndSettle();

      expect(find.byType(ElevatedButton), findsOneWidget);
      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
    });

    testWidgets('4. VolunteerTaskHistoryScreen (V6) renders pinned stats and filter chips', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final taskProv = VolunteerTaskProvider();
      taskProv.setTasksForTesting([
        DonationModel(
          id: 1,
          donorId: 10,
          foodName: 'Meals (50 Meals)',
          foodCategory: 'Cooked Food',
          quantity: 50.0,
          quantityUnit: 'Meals',
          preparationTime: '2026-09-27T12:00:00Z',
          expiryTime: '2026-09-27T16:00:00Z',
          pickupAddress: 'Anna Nagar, Chennai',
          status: 'completed',
          createdAt: '2026-09-27T12:00:00Z',
          ngoName: 'Annam Relief Foundation',
        ),
      ]);

      await tester.pumpWidget(wrapWithProviders(
        const VolunteerTaskHistoryScreen(),
        volunteerTaskProvider: taskProv,
      ));
      await tester.pumpAndSettle();

      expect(find.widgetWithText(AppBar, 'Task History'), findsOneWidget);
      expect(find.text('50'), findsOneWidget);
      expect(find.text('Meals (50 Meals)'), findsOneWidget);
      expect(find.text('Anna Nagar, Chennai'), findsOneWidget);
    });

    testWidgets('5. NgoReceivingDistributionScreen (N5) renders operational triple tracking and actions', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final donation = DonationModel(
        id: 201,
        donorId: 5,
        foodName: 'Cooked Rice & Dal',
        foodCategory: 'Cooked Food',
        quantity: 50.0,
        quantityUnit: 'Meals',
        preparationTime: '2026-09-27T12:00:00Z',
        expiryTime: '2026-09-27T16:00:00Z',
        pickupAddress: 'Sector 5, Salt Lake',
        status: 'assigned',
        createdAt: '2026-09-27T12:00:00Z',
      );

      await tester.pumpWidget(wrapWithProviders(
        NgoReceivingDistributionScreen(donationId: 201, donation: donation),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Receiving & Distribution'), findsOneWidget);
      expect(find.text('EXPECTED'), findsOneWidget);
      expect(find.text('RECEIVED'), findsOneWidget);
      expect(find.text('DISTRIBUTED'), findsOneWidget);
      expect(find.textContaining('Confirm Receipt'), findsAtLeastNWidgets(1));
      expect(find.textContaining('Log Distribution'), findsAtLeastNWidgets(1));
    });

    testWidgets('6. AdminAuditLogScreen (A7) renders security audit cards and filters', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final sampleLogs = [
        {
          'id': 1,
          'action': 'login',
          'resource_type': 'user',
          'resource_id': 1,
          'actor_email': 'admin@smartfood.org',
          'actor_role': 'admin',
          'status': 'success',
          'created_at': DateTime.now().toIso8601String(),
        },
        {
          'id': 2,
          'action': 'ngo_verification',
          'resource_type': 'ngo',
          'resource_id': 5,
          'actor_email': 'admin@smartfood.org',
          'actor_role': 'admin',
          'status': 'success',
          'created_at': DateTime.now().toIso8601String(),
        },
      ];

      await tester.pumpWidget(wrapWithProviders(AdminAuditLogScreen(initialLogs: sampleLogs)));
      await tester.pumpAndSettle();

      expect(find.text('A7: Security Audit Log'), findsOneWidget);
      expect(find.text('All Events'), findsOneWidget);
      expect(find.text('Rescues & Assignments'), findsOneWidget);
      expect(find.text('OTP Verification'), findsOneWidget);
      expect(find.text('Authentication'), findsOneWidget);
      expect(find.text('Security Interventions'), findsOneWidget);
    });

    testWidgets('7. AvailabilityToggle displays tri-state availability', (tester) async {
      String? updatedStatus;
      await tester.pumpWidget(wrapWithProviders(
        Scaffold(
          body: Center(
            child: AvailabilityToggle(
              currentStatus: 'available',
              onStatusChanged: (status) => updatedStatus = status,
            ),
          ),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(AvailabilityToggle), findsOneWidget);

      await tester.tap(find.byType(AvailabilityToggle));
      await tester.pumpAndSettle();

      // Tap '🟡 On Active Task' in popup menu
      await tester.tap(find.text('🟡 On Active Task'));
      await tester.pumpAndSettle();

      expect(updatedStatus, 'busy');
    });

    testWidgets('8. Trilingual translation parity for new authoritative keys', (tester) async {
      final keys = [
        'verification_pending_title',
        'confirm_receipt',
        'log_distribution',
        'vehicle_profile',
        'audit_log_title',
        'forgot_password_title',
      ];

      for (final key in keys) {
        expect(LocaleProvider.translations['en']![key], isNotNull, reason: 'Key $key missing in EN');
        expect(LocaleProvider.translations['ta']![key], isNotNull, reason: 'Key $key missing in TA');
        expect(LocaleProvider.translations['hi']![key], isNotNull, reason: 'Key $key missing in HI');
      }
    });

  });
}
