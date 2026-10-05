import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/models/ngo_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/ngo_provider.dart';
import 'package:smart_food_waste_donation/providers/notification_provider.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_dashboard.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_food_requirements_screen.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_receiving_distribution_screen.dart';
import 'package:smart_food_waste_donation/screens/ngo/ngo_verification_pending_screen.dart';
import 'package:smart_food_waste_donation/widgets/donation_card.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

Widget _buildTestApp(
  Widget child, {
  UserModel? user,
  NgoModel? ngo,
  List<DonationModel>? donations,
  DonationModel? currentDetail,
  String language = 'en',
}) {
  final lp = LocaleProvider();
  lp.setLanguageSyncForTesting(language);

  final auth = AuthProvider();
  if (user != null) {
    auth.setCurrentUserForTesting(user);
  }

  final ngoProv = NgoProvider();
  if (ngo != null) {
    ngoProv.setMyNgoForTesting(ngo);
  }

  final donProv = DonationProvider();
  if (donations != null) {
    donProv.setDonationsForTesting(donations);
  }
  if (currentDetail != null) {
    donProv.setCurrentDetailForTesting(currentDetail);
  }

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider<NgoProvider>.value(value: ngoProv),
      ChangeNotifierProvider<DonationProvider>.value(value: donProv),
      ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
    ],
    child: MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(
        body: child,
      ),
    ),
  );
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 4 Complete NGO Role Implementation Tests', () {
    final ngoUser = UserModel(
      id: 201,
      name: 'Annam Food Bank',
      email: 'contact@annambank.org',
      phone: '+91 94444 12345',
      role: 'ngo',
      isActive: true,
      address: '45 Temple Street, Madurai',
    );

    final verifiedNgo = NgoModel(
      id: 1,
      userId: 201,
      organizationName: 'Annam Food Bank',
      contactPhone: '+91 94444 12345',
      address: '45 Temple Street, Madurai',
      capacity: 250,
      currentCapacity: 250,
      isAvailable: true,
      isVerified: true,
      demandRequirements: {'Cooked Food': 150, 'Bakery': 50},
      operatingHours: {
        'monday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
        'tuesday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
      },
    );

    final unverifiedNgo = NgoModel(
      id: 2,
      userId: 201,
      organizationName: 'Karunai Foundation',
      contactPhone: '+91 94444 67890',
      address: '12 North Gate, Madurai',
      capacity: 100,
      currentCapacity: 100,
      isAvailable: true,
      isVerified: false,
    );

    final nowStr = DateTime.now().toIso8601String();
    final expiryStr = DateTime.now().add(const Duration(hours: 4)).toIso8601String();

    // ── 1. NGO NAVIGATION (EXACTLY 3 TABS) ───────────────────────────────────
    testWidgets('1. NGO bottom navigation bar contains exactly 3 tabs (Dashboard, Requirements, Profile)', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const RoleBottomNav(currentRole: 'ngo', currentIndex: 0),
          user: ngoUser,
          ngo: verifiedNgo,
        ),
      );
      await tester.pumpAndSettle();

      final bottomNavFinder = find.byType(NavigationBar);
      expect(bottomNavFinder, findsOneWidget);

      final navBar = tester.widget<NavigationBar>(bottomNavFinder);
      expect(navBar.destinations.length, 3);

      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Requirements'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);
    });

    // ── 2. VERIFICATION GATE ────────────────────────────────────────────────
    testWidgets('2. Unverified NGO is gated by verification-pending screen, blocking rescue acceptance', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: unverifiedNgo,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.byType(NgoVerificationPendingScreen), findsOneWidget);
      expect(find.text('Verification pending'), findsOneWidget);
      expect(find.text('Karunai Foundation is under review. You can accept donations once an admin verifies your organisation.'), findsOneWidget);
      expect(find.text('Check status'), findsOneWidget);
      expect(find.text('Log out'), findsOneWidget);

      // Verify no rescue cards or acceptance buttons are accessible
      expect(find.byType(DonationCard), findsNothing);
      expect(find.text('ACCEPT RESCUE'), findsNothing);
    });

    // ── 3. NGO DASHBOARD & RESCUE CARD DETAILS ──────────────────────────────
    testWidgets('3. Verified NGO dashboard displays available rescue card with full details and verified partner badge', (tester) async {
      final sampleDonation = DonationModel(
        id: 501,
        donorId: 101,
        foodName: 'South Indian Thali',
        quantity: 50.0,
        quantityUnit: 'Meals',
        foodCategory: 'Cooked Food',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Urgent',
        rescueUrgencyLevel: 'Urgent',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'pending',
        pickupAddress: 'Hotel Saravana Bhavan, Madurai',
        currentDistanceKm: 2.1,
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
        remainingMinutes: 60,
      );

      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
          donations: [sampleDonation],
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('South Indian Thali'), findsOneWidget);
      expect(find.textContaining('50 Meals'), findsOneWidget);
      expect(find.text('Rescue feasible'), findsOneWidget);
      expect(find.text('ACCEPT RESCUE'), findsOneWidget);
      expect(find.text('PASS'), findsOneWidget);
      expect(find.text('Verified Partner'), findsWidgets);
      // Location is masked before acceptance
      expect(find.textContaining('Masked'), findsOneWidget);
      expect(find.text('Share Rescue'), findsOneWidget);
      expect(find.text('Report Issue'), findsOneWidget);
    });

    // ── 4. SMALL DONATION INDICATOR ─────────────────────────────────────────
    testWidgets('4. Small donation (<= 15 meals) displays Self-pickup preferred indicator', (tester) async {
      final smallDonation = DonationModel(
        id: 502,
        donorId: 101,
        foodName: 'Bread and Pastries',
        quantity: 12.0,
        quantityUnit: 'Meals',
        foodCategory: 'Bakery',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Fresh',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'pending',
        pickupAddress: 'City Bakery',
        currentDistanceKm: 1.2,
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
        remainingMinutes: 90,
      );

      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
          donations: [smallDonation],
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Bread and Pastries'), findsOneWidget);
      expect(find.text('Self-pickup preferred'), findsOneWidget);
    });

    // ── 5. REJECTION REASON CAPTURE ─────────────────────────────────────────
    testWidgets('5. Tapping Pass opens bottom sheet with 6 rejection reasons', (tester) async {
      final sampleDonation = DonationModel(
        id: 503,
        donorId: 101,
        foodName: 'Fried Rice',
        quantity: 30.0,
        quantityUnit: 'Meals',
        foodCategory: 'Cooked Food',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Fresh',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'pending',
        pickupAddress: 'Dragon Wok',
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
        remainingMinutes: 60,
      );

      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
          donations: [sampleDonation],
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      final passBtn = find.text('PASS');
      expect(passBtn, findsOneWidget);
      await tester.ensureVisible(passBtn);
      await tester.pumpAndSettle();
      await tester.tap(passBtn);
      await tester.pumpAndSettle();

      expect(find.text('Select Reason for Passing'), findsOneWidget);
      expect(find.text('Capacity full'), findsOneWidget);
      expect(find.text('Food not required'), findsOneWidget);
      expect(find.text('Facility closed'), findsOneWidget);
      expect(find.text('Pickup unavailable'), findsOneWidget);
      expect(find.text('Too far away'), findsOneWidget);
      expect(find.text('Other reason'), findsOneWidget);
      expect(find.text('Confirm Pass'), findsOneWidget);

      await tester.tap(find.text('Too far away'));
      await tester.pumpAndSettle();
    });

    // ── 6. ACCEPTANCE MODAL WITH METHOD CHOICE ──────────────────────────────
    testWidgets('6. Tapping Accept Rescue presents Collect Yourself and Request Volunteer options', (tester) async {
      final sampleDonation = DonationModel(
        id: 504,
        donorId: 101,
        foodName: 'Mixed Veg Curry',
        quantity: 10.0,
        quantityUnit: 'Meals',
        foodCategory: 'Cooked Food',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Fresh',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'pending',
        pickupAddress: 'Spice Garden',
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
        remainingMinutes: 60,
      );

      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
          donations: [sampleDonation],
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      final acceptBtn = find.text('ACCEPT RESCUE');
      expect(acceptBtn, findsOneWidget);
      await tester.ensureVisible(acceptBtn);
      await tester.pumpAndSettle();
      await tester.tap(acceptBtn);
      await tester.pumpAndSettle();

      expect(find.text('Choose Collection Mode'), findsOneWidget);
      expect(find.text('COLLECT YOURSELF'), findsOneWidget);
      expect(find.text('REQUEST VOLUNTEER'), findsOneWidget);
      // Small donation tag inside sheet
      expect(find.text('Self-pickup preferred'), findsWidgets);
    });

    // ── 7. IN-TRANSIT RESCUE & HANDOVER MODES ───────────────────────────────
    testWidgets('7. In-Transit tab supports Self-Pickup with OTP verification and Donor Self-Dropoff', (tester) async {
      final selfPickupDonation = DonationModel(
        id: 601,
        donorId: 101,
        foodName: 'Chapati & Dal',
        quantity: 40.0,
        quantityUnit: 'Meals',
        foodCategory: 'Cooked Food',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Urgent',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'accepted',
        pickupMode: 'self_pickup',
        pickupAddress: 'Community Center, Madurai',
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
      );

      final donorDropoffDonation = DonationModel(
        id: 602,
        donorId: 101,
        foodName: 'Fruit Baskets',
        quantity: 25.0,
        quantityUnit: 'Meals',
        foodCategory: 'Fruits',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Fresh',
        feasibilityStatus: 'RESCUE_FEASIBLE',
        status: 'accepted',
        pickupMode: 'donor_dropoff',
        pickupAddress: 'Farm Direct',
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
      );

      await tester.pumpWidget(
        _buildTestApp(
          const NgoDashboardScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
          donations: [selfPickupDonation, donorDropoffDonation],
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Switch to In-Progress tab (value 1)
      await tester.tap(find.byIcon(Icons.local_shipping_outlined));
      await tester.pumpAndSettle();

      // Check self-pickup card features
      expect(find.text('NGO Self-Pickup in progress'), findsOneWidget);
      expect(find.text('Verify Donor OTP'), findsOneWidget);
      expect(find.text('Switch to Volunteer Courier'), findsOneWidget);

      // Check donor self-dropoff card features
      expect(find.text('Donor Self-Dropoff in progress'), findsOneWidget);
    });

    // ── 8. REQUIREMENTS TAB & PERSISTENT DEMAND ─────────────────────────────
    testWidgets('8. Requirements tab displays persistent capacity, demands, hours, and dismissible reminder banner', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const NgoFoodRequirementsScreen(),
          user: ngoUser,
          ngo: verifiedNgo,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Reminder banner
      expect(find.text('Intake & Schedule Verification'), findsOneWidget);
      expect(find.text('Values remain active until updated. Verify your daily meal capacity and operating hours.'), findsOneWidget);
      expect(find.text('All Good'), findsOneWidget);

      // Dismiss reminder
      await tester.tap(find.text('All Good'));
      await tester.pumpAndSettle();
      expect(find.text('Intake & Schedule Verification'), findsNothing);

      // Intake capacity & demands
      expect(find.text("Today's Intake Capacity"), findsOneWidget);
      expect(find.textContaining('250'), findsWidgets);
      expect(find.text('Food Category'), findsOneWidget);
      expect(find.text('Cooked Food'), findsOneWidget);
      expect(find.text('Operating & Kitchen Hours'), findsOneWidget);
      expect(find.text('CONFIRM'), findsOneWidget);

      // Bottom nav is intact with 3 tabs and requirements active
      final navBar = tester.widget<NavigationBar>(find.byType(NavigationBar));
      expect(navBar.destinations.length, 3);
      expect(navBar.selectedIndex, 1);
    });

    // ── 9. RECEIVING & BATCH DISTRIBUTION ───────────────────────────────────
    testWidgets('9. Receiving & Distribution tracks expected vs received, logs batches, and computes remaining quantity', (tester) async {
      final detail = DonationModel(
        id: 701,
        donorId: 101,
        foodName: 'Vegetable Biryani',
        quantity: 50.0,
        quantityUnit: 'Meals',
        foodCategory: 'Cooked Food',
        aiVisualCondition: 'Good',
        urgencyLevel: 'Fresh',
        status: 'delivered',
        pickupAddress: 'Royal Palace Dining',
        createdAt: nowStr,
        preparationTime: nowStr,
        expiryTime: expiryStr,
      );

      await tester.pumpWidget(
        _buildTestApp(
          NgoReceivingDistributionScreen(
            donationId: 701,
            donation: detail,
          ),
          user: ngoUser,
          ngo: verifiedNgo,
          currentDetail: detail,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // 4 Metric Tiles
      expect(find.text('EXPECTED'), findsOneWidget);
      expect(find.text('RECEIVED'), findsOneWidget);
      expect(find.text('DISTRIBUTED'), findsOneWidget);
      expect(find.text('REMAINING'), findsOneWidget);

      // Non-binding disclaimer
      expect(
        find.text('All metrics are non-binding estimates. No tax deduction or write-off claims are provided.'),
        findsOneWidget,
      );

      // Log distribution section
      expect(find.text('2. Log Distribution'), findsOneWidget);
      expect(find.text('LOG DISTRIBUTION'), findsOneWidget);
    });

    // ── 10. LOCALIZATION (TAMIL & HINDI) ────────────────────────────────────
    testWidgets('10. Phase 4 NGO strings are localized accurately across English, Tamil, and Hindi', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          Builder(
            builder: (context) {
              return Column(
                children: [
                  Text(context.tr('reject_reason_title')),
                  Text(context.tr('small_donation_pref')),
                  Text(context.tr('requirements_reminder_title')),
                  Text(context.tr('share_rescue_btn')),
                  Text(context.tr('donor_dropoff_in_progress')),
                ],
              );
            },
          ),
          language: 'ta',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('காரணத்தைத் தேர்ந்தெடுக்கவும்'), findsOneWidget);
      expect(find.text('நேரடி சேகரிப்பு பரிந்துரைக்கப்படுகிறது'), findsOneWidget);
      expect(find.text('கொள்ளளவு மற்றும் அட்டவணை சரிபார்ப்பு'), findsOneWidget);
      expect(find.text('மீட்பைப் பகிர்'), findsOneWidget);
      expect(find.text('வழங்குநரின் நேரடி விநியோகம் நடைபெறுகிறது'), findsOneWidget);

      // Test Hindi
      await tester.pumpWidget(
        _buildTestApp(
          Builder(
            builder: (context) {
              return Column(
                children: [
                  Text(context.tr('reject_reason_title')),
                  Text(context.tr('small_donation_pref')),
                  Text(context.tr('requirements_reminder_title')),
                  Text(context.tr('share_rescue_btn')),
                  Text(context.tr('donor_dropoff_in_progress')),
                ],
              );
            },
          ),
          language: 'hi',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('कारण चुनें'), findsOneWidget);
      expect(find.text('स्वयं पिकअप अनुशंसित'), findsOneWidget);
      expect(find.text('क्षमता और समय सारिणी सत्यापन'), findsOneWidget);
      expect(find.text('बचाव साझा करें'), findsOneWidget);
      expect(find.text('दाता द्वारा स्वयं वितरण प्रगति पर है'), findsOneWidget);
    });
  });
}
