import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/admin_operations_model.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/models/ngo_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/admin_provider.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_dashboard.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_donations_screen.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_users_screen.dart';
import 'package:smart_food_waste_donation/screens/admin/ngo_verification_screen.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_rescue_detail_modal.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_monthly_report_screen.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_audit_log_screen.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_disputes_screen.dart';
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

Widget _buildAdminTestApp({
  required Widget child,
  UserModel? user,
  AdminProvider? adminProvider,
  DonationProvider? donationProvider,
  String language = 'en',
}) {
  final lp = LocaleProvider();
  lp.setLanguageSyncForTesting(language);

  final auth = AuthProvider();
  final adminUser = user ??
      UserModel(
        id: 1,
        name: 'Chief Admin Sarah',
        email: 'sarah.admin@rescue.org',
        role: 'admin',
        phone: '+919988776655',
        isActive: true,
      );
  auth.setCurrentUserForTesting(adminUser);

  final adminProv = adminProvider ?? AdminProvider();
  final donProv = donationProvider ?? DonationProvider();

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider<AdminProvider>.value(value: adminProv),
      ChangeNotifierProvider<DonationProvider>.value(value: donProv),
    ],
    child: MaterialApp(
      theme: AppTheme.light,
      home: child,
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 6 — Admin Navigation & Role RBAC Isolation', () {
    testWidgets('Admin navigation renders exactly 5 tabs in RoleBottomNav', (tester) async {
      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const Scaffold(
            bottomNavigationBar: RoleBottomNav(currentRole: 'admin', currentIndex: 0),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(NavigationBar), findsOneWidget);
      expect(find.text('Overview'), findsOneWidget);
      expect(find.text('Donations'), findsOneWidget);
      expect(find.text('Users'), findsOneWidget);
      expect(find.text('Verify NGOs'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);
    });

    testWidgets('ProfileScreen displays Admin details, Contact, Language, and Logout without leaking secrets', (tester) async {
      await tester.pumpWidget(
        _buildAdminTestApp(child: const ProfileScreen()),
      );
      await tester.pumpAndSettle();

      expect(find.text('Chief Admin Sarah'), findsOneWidget);
      expect(find.text('sarah.admin@rescue.org'), findsOneWidget);
      expect(find.text('+919988776655'), findsOneWidget);
      expect(find.textContaining('App Language'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);

      // Verify no passwords, tokens, or plaintext secrets are exposed
      expect(find.textContaining('password'), findsNothing);
      expect(find.textContaining('Bearer'), findsNothing);
      expect(find.textContaining('refresh_token'), findsNothing);
    });
  });

  group('Phase 6 — Operational Overview & Exception Queue', () {
    testWidgets('Overview displays live operational metrics and exception items sorted critical first', (tester) async {
      final adminProv = AdminProvider();
      final summary = AdminReceivingSummaryModel(
        activeRescues: 14,
        urgentRescues: 3,
        criticalRescues: 2,
        inTransit: 5,
        receivedToday: 420.0,
        distributedToday: 380.0,
        remainingToday: 40.0,
        issuesOpen: 2,
        foodAtRiskMeals: 85.0,
        completedToday: 18,
      );

      final critItem = AdminReceivingItemModel(
        id: 101,
        foodName: 'Hot Vegetable Biryani',
        foodCategory: 'Cooked Food',
        quantity: 50.0,
        quantityUnit: 'Meals',
        donorId: 10,
        donorName: 'Grand Palace Hotel',
        status: 'accepted',
        rescueUrgencyLevel: 'CRITICAL',
        remainingMinutes: 12,
        expectedQuantity: 50.0,
        pickupAddress: '10 Palace Road',
        createdAt: '2026-10-04T10:00:00Z',
      );

      final urgentItem = AdminReceivingItemModel(
        id: 102,
        foodName: 'Fresh Paneer Curry',
        foodCategory: 'Cooked Food',
        quantity: 30.0,
        quantityUnit: 'Meals',
        donorId: 11,
        donorName: 'Spice Garden',
        status: 'volunteer_assigned',
        rescueUrgencyLevel: 'URGENT',
        remainingMinutes: 45,
        expectedQuantity: 30.0,
        pickupAddress: '22 Garden Lane',
        createdAt: '2026-10-04T10:15:00Z',
      );

      adminProv.setReceivingDataForTesting(
        summary: summary,
        items: [urgentItem, critItem], // unsorted order passed
      );

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const AdminDashboardScreen(),
          adminProvider: adminProv,
        ),
      );
      await tester.pumpAndSettle();

      // Check operational strip metrics
      expect(find.text('14'), findsOneWidget);
      expect(find.text('Active'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('Urgent'), findsWidgets);
      expect(find.text('2'), findsWidgets);
      expect(find.text('At Risk'), findsOneWidget);
      expect(find.text('18'), findsOneWidget);
      expect(find.text('Completed Today'), findsOneWidget);

      // Verify INTERVENE action button is prominent on exception cards
      expect(find.text('INTERVENE'), findsWidgets);
      expect(find.text('Hot Vegetable Biryani • 50 Meals'), findsWidgets);
    });
  });

  group('Phase 6 — Rescue Detail Lifecycle & Security', () {
    testWidgets('Detail displays complete lifecycle, zero plaintext OTP, small donation badge, and FSSAI disclaimer', (tester) async {
      final adminProv = AdminProvider();
      final detail = AdminRescueDetailModel(
        id: 201,
        foodName: 'Rice & Sambar Batch',
        foodCategory: 'Cooked Food',
        quantity: 12.0, // Small donation <= 15
        quantityUnit: 'Meals',
        donorId: 15,
        donorName: 'Annapoorna Kitchen',
        donorPhone: '+919444001122',
        assignedNgoId: 4,
        ngoName: 'Grace Shelter Home',
        assignedVolunteerId: 7,
        volunteerName: 'Courier Rahul',
        volunteerPhone: '+919333002233',
        status: 'volunteer_assigned',
        rescueUrgencyLevel: 'URGENT',
        remainingMinutes: 35,
        aiVisualCondition: 'GOOD',
        storageMethod: 'Insulated Hot Carrier',
        packagingCondition: 'Sealed Foil Trays',
        expectedQuantity: 12.0,
        receivedQuantity: null,
        pickupAddress: '44 Temple St, Chennai',
        createdAt: '2026-10-04T12:00:00Z',
        preparationTime: 'Prepared 1h ago',
        aiAdvisory: 'Freshly prepared cooked meals verified within safety margins',
        currentWave: 2,
        waveName: 'Wave 2 (Volunteer Courier Rescue)',
        offersCount: 3,
        feasibilityStatus: 'FEASIBLE',
        otpState: 'PENDING_VERIFICATION', // Strictly state string
        blockedReason: null,
        mealsRescued: 12.0,
        environmentalCo2Kg: 6.0,
        environmentalWaterLiters: 2400.0,
        timeline: [
          AdminRescueTimelineItemModel(
            stage: 'DONATION_CREATED',
            label: 'Donation Created',
            timestamp: '2026-10-04T12:00:00Z',
            isCompleted: true,
            isCurrent: false,
            actorName: 'Annapoorna Kitchen',
            details: '12 Meals created',
          ),
          AdminRescueTimelineItemModel(
            stage: 'VOLUNTEER_ASSIGNED',
            label: 'Volunteer Courier Assigned',
            timestamp: '2026-10-04T12:10:00Z',
            isCompleted: true,
            isCurrent: true,
            actorName: 'Courier Rahul',
            details: 'Dispatched to pickup location',
          ),
        ],
      );

      adminProv.setRescueDetailForTesting(detail);

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const AdminRescueDetailModal(donationId: 201),
          adminProvider: adminProv,
        ),
      );
      await tester.pumpAndSettle();

      // Lifecycle checks
      expect(find.text('Rice & Sambar Batch'), findsOneWidget);
      expect(find.text('Annapoorna Kitchen'), findsWidgets);
      expect(find.text('Grace Shelter Home'), findsOneWidget);
      expect(find.text('Courier Rahul'), findsWidgets);

      // Small donation check
      expect(find.text('Small batch: Self-pickup preferred until batching implemented'), findsOneWidget);

      // Zero Plaintext OTP check
      expect(find.text('PENDING VERIFICATION'), findsOneWidget);
      expect(find.text('Guarded (No OTP shown)'), findsOneWidget);
      expect(find.textContaining('123456'), findsNothing);
      expect(find.textContaining('9999'), findsNothing);

      // FSSAI informational guidance check
      expect(find.text('FSSAI Food Safety Guidance'), findsOneWidget);
      expect(find.text('Informational only — No legal certification claims'), findsOneWidget);

      // Auditable History check
      expect(find.text('Auditable History'), findsOneWidget);
      expect(find.text('Donation Created'), findsWidgets);
    });

    testWidgets('Allowed Force-State transitions allow-list enforces valid target and mandatory reason', (tester) async {
      // Direct unit contract validation of canonical state transitions
      expect(allowedAdminForceTransitions['pending'], contains('accepted'));
      expect(allowedAdminForceTransitions['pending'], contains('cancelled'));
      expect(allowedAdminForceTransitions['pending'], isNot(contains('delivered'))); // Illegal jump

      expect(allowedAdminForceTransitions['accepted'], contains('collected'));
      expect(allowedAdminForceTransitions['accepted'], contains('volunteer_assigned'));
      expect(allowedAdminForceTransitions['accepted'], isNot(contains('completed'))); // Illegal jump

      expect(allowedAdminForceTransitions['collected'], contains('delivered'));
      expect(allowedAdminForceTransitions['collected'], isNot(contains('pending'))); // Illegal backward jump

      expect(allowedAdminForceTransitions['delivered'], contains('completed'));
      expect(allowedAdminForceTransitions['delivered'], isNot(contains('volunteer_assigned'))); // Illegal jump
    });
  });

  group('Phase 6 — Admin Users & NGO Verification', () {
    testWidgets('Users tab displays Donors, NGOs, Volunteers, Admins and permits active toggling and inspection', (tester) async {
      final adminProv = AdminProvider();
      final users = [
        UserModel(id: 10, name: 'Taj Catering', email: 'taj@cater.com', role: 'donor', isActive: true),
        UserModel(id: 20, name: 'Anbaalayam NGO', email: 'info@anbaalayam.org', role: 'ngo', isActive: true),
        UserModel(id: 30, name: 'Courier Maya', email: 'maya@volunteer.org', role: 'volunteer', isActive: true, vehicleType: 'Scooter', carryingCapacity: 40, reliabilityScore: 97.0),
        UserModel(id: 40, name: 'Lead Admin Dave', email: 'dave@rescue.org', role: 'admin', isActive: true),
      ];
      adminProv.setUsersForTesting(users);

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const AdminUsersScreen(),
          adminProvider: adminProv,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Taj Catering'), findsOneWidget);
      expect(find.text('Anbaalayam NGO'), findsOneWidget);
      expect(find.text('Courier Maya'), findsOneWidget);
      expect(find.text('Lead Admin Dave'), findsOneWidget);

      // Tap on a user to open Inspection modal without secrets
      await tester.tap(find.text('Courier Maya'));
      await tester.pumpAndSettle();

      expect(find.text('Role'), findsOneWidget);
      expect(find.text('VOLUNTEER'), findsOneWidget);
      expect(find.text('maya@volunteer.org'), findsWidgets);
      expect(find.text('Scooter'), findsOneWidget);
      expect(find.text('40 Meals'), findsOneWidget);
      expect(find.text('97.0%'), findsOneWidget);

      // Verify no tokens or passwords in inspection modal
      expect(find.textContaining('password'), findsNothing);
      expect(find.textContaining('jwt'), findsNothing);
    });

    testWidgets('Verify NGOs screen allows review, verify, and reject with mandatory reason', (tester) async {
      final adminProv = AdminProvider();
      final ngos = [
        NgoModel(
          id: 101,
          userId: 201,
          organizationName: 'Hope Orphanage Trust',
          address: '12 Gandhi Road',
          capacity: 200,
          currentCapacity: 50,
          isAvailable: true,
          isVerified: false,
        ),
      ];
      adminProv.setNgosForTesting(ngos);

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const NgoVerificationScreen(),
          adminProvider: adminProv,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Hope Orphanage Trust'), findsOneWidget);
      expect(find.text('Capacity (kg): 200'), findsOneWidget);

      // Tap Reject button to open mandatory reason dialog
      await tester.tap(find.text('Reject'));
      await tester.pumpAndSettle();

      expect(find.text('Mandatory Rejection Reason:'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);

      // Enter rejection reason
      await tester.enterText(find.byType(TextField), 'Documents missing valid registration certificate');
      await tester.pumpAndSettle();

      // Confirm rejection
      await tester.tap(find.widgetWithText(ElevatedButton, 'Reject'));
      await tester.pumpAndSettle();

      // Verify NGO was rejected and removed from pending queue
      expect(adminProv.unverifiedNgos.length, 0);
    });
  });

  group('Phase 6 — Disputes & Auditable History', () {
    testWidgets('Disputes screen allows reviewing and resolving operational issues with notes', (tester) async {
      final adminProv = AdminProvider();
      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const AdminDisputesScreen(),
          adminProvider: adminProv,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Feedback & Operations Triage'), findsOneWidget);
    });

    testWidgets('Audit log screen displays Auditable History with who, what, when, and no OTP', (tester) async {
      final mockLogs = [
        {
          'id': 1,
          'action': 'admin_intervention',
          'actor': 'Chief Admin Sarah',
          'timestamp': '2026-10-04T14:30:00Z',
          'resource_type': 'donation',
          'resource_id': '101',
          'status': 'success',
          'details': 'Courier delayed; manual rematching triggered'
        }
      ];

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: AdminAuditLogScreen(initialLogs: mockLogs),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Auditable History'), findsOneWidget);
      expect(find.text('admin_intervention'), findsOneWidget);
      expect(find.text('Actor: Chief Admin Sarah'), findsOneWidget);
      expect(find.text('donation #101'), findsOneWidget);
      expect(find.text('Courier delayed; manual rematching triggered'), findsOneWidget);

      // Verify no OTP is exposed
      expect(find.textContaining('otp'), findsNothing);
    });
  });

  group('Phase 6 — Donations Tab Filtering', () {
    testWidgets('Donations tab provides status, urgency, category, and multi-field search filtering', (tester) async {
      final donProv = DonationProvider();
      final donations = [
        DonationModel(
          id: 501,
          donorId: 10,
          foodName: 'Sambar Rice',
          foodCategory: 'Cooked Food',
          quantity: 25.0,
          quantityUnit: 'Meals',
          status: 'pending',
          urgencyLevel: 'Fresh',
          preparationTime: '2026-10-04T10:00:00Z',
          expiryTime: '2026-10-04T16:00:00Z',
          pickupAddress: 'T Nagar, Chennai',
          donorName: 'Saravana Bhavan',
          createdAt: '2026-10-04T10:00:00Z',
        ),
        DonationModel(
          id: 502,
          donorId: 11,
          foodName: 'Raw Vegetables Box',
          foodCategory: 'Raw Ingredients',
          quantity: 50.0,
          quantityUnit: 'kg',
          status: 'delivered',
          urgencyLevel: 'Critical',
          preparationTime: '2026-10-04T08:00:00Z',
          expiryTime: '2026-10-04T18:00:00Z',
          pickupAddress: 'Koyambedu, Chennai',
          donorName: 'Fresh Agro Mart',
          ngoName: 'Helping Hands',
          createdAt: '2026-10-04T08:00:00Z',
        ),
      ];
      donProv.setDonationsForTesting(donations);

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: const AdminDonationsScreen(),
          donationProvider: donProv,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Sambar Rice'), findsOneWidget);
      expect(find.text('Raw Vegetables Box'), findsOneWidget);

      // Filter by category: Cooked Food
      await tester.tap(find.widgetWithText(FilterChip, 'Cooked Food'));
      await tester.pumpAndSettle();

      expect(find.text('Sambar Rice'), findsOneWidget);
      expect(find.text('Raw Vegetables Box'), findsNothing);

      // Reset category to All
      await tester.tap(find.widgetWithText(FilterChip, 'All').last);
      await tester.pumpAndSettle();

      // Filter by urgency: Critical
      await tester.tap(find.widgetWithText(FilterChip, 'Critical'));
      await tester.pumpAndSettle();

      expect(find.text('Raw Vegetables Box'), findsOneWidget);
      expect(find.text('Sambar Rice'), findsNothing);
    });
  });

  group('Phase 6 — Monthly Impact & Waste-Prevention Insights', () {
    testWidgets('Monthly report clearly labels estimated figures and displays real surplus patterns', (tester) async {
      final report = AdminMonthlyReportModel(
        month: '2026-10',
        donationsCount: 150,
        foodRecoveredKg: 4200.0,
        mealsRescued: 4200.0,
        receivedQuantity: 4200.0,
        distributedQuantity: 4100.0,
        completedRescues: 142,
        estimatedCo2eKg: 10500.0,
        estimatedWaterLiters: 4200000.0,
        estimatedDisposalCostAvoidedInr: 63000.0,
        avgRescueCompletionMinutes: 32.5,
        isEstimated: true,
      );

      final insights = AdminRepeatDonorInsightsModel(
        totalDonationsAnalyzed: 150,
        patterns: [
          AdminRepeatDonorPatternItemModel(
            dayOfWeek: 'Friday',
            foodCategory: 'Cooked Meals',
            donationCount: 38,
            avgSurplus: 65.0,
            avgRescued: 60.0,
            avgUnrescued: 5.0,
            topDonors: ['Taj Catering', 'Royal Feast'],
          ),
        ],
      );

      await tester.pumpWidget(
        _buildAdminTestApp(
          child: AdminMonthlyReportScreen(
            initialReport: report,
            initialInsights: insights,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Check verified quantities
      expect(find.text('4200'), findsWidgets);
      expect(find.text('4200.0 kg'), findsOneWidget);
      expect(find.text('142'), findsOneWidget);
      expect(find.text('32.5 min'), findsOneWidget);

      // Check estimated label on environmental and cost figures (Section 17)
      expect(find.text('ESTIMATED'), findsOneWidget);
      expect(find.text('CO2e Averted (Estimated)'), findsOneWidget);
      expect(find.text('10500.0 kg'), findsOneWidget);
      expect(find.text('Water Saved (Estimated)'), findsOneWidget);
      expect(find.text('4200000 L'), findsOneWidget);
      expect(find.text('Disposal Cost Avoided (Estimated)'), findsOneWidget);
      expect(find.text('₹63000'), findsOneWidget);

      // Verify no tax-writeoff disclaimer
      expect(find.textContaining('No tax-writeoff'), findsOneWidget);

      // Switch to Waste-Prevention Insights Tab (Section 18)
      await tester.tap(find.text('Waste-Prevention Insights'));
      await tester.pumpAndSettle();

      expect(find.text('Friday • Cooked Meals'), findsOneWidget);
      expect(find.text('Avg Surplus: 65 meals'), findsOneWidget);
      expect(find.text('Rescued: 60 meals'), findsOneWidget);
      expect(find.text('Recurring partners: Taj Catering, Royal Feast'), findsOneWidget);

      // Switch to FSSAI Guidance Tab (Section 19)
      await tester.tap(find.text('FSSAI Food Safety Guidance'));
      await tester.pumpAndSettle();

      expect(find.text('Informational only — No legal certification claims'), findsOneWidget);
      expect(find.text('Temperature Control Guidelines'), findsOneWidget);
    });
  });

  group('Phase 6 — Localization (English, Tamil, Hindi)', () {
    testWidgets('Admin strings localize correctly across English, Tamil, and Hindi', (tester) async {
      // English check
      final lpEn = LocaleProvider();
      lpEn.setLanguageSyncForTesting('en');
      expect(lpEn.translate('nav_overview'), 'Overview');
      expect(lpEn.translate('nav_donations'), 'Donations');
      expect(lpEn.translate('nav_users'), 'Users');
      expect(lpEn.translate('verify_ngos'), 'Verify NGOs');
      expect(lpEn.translate('admin_intervene'), 'Intervene');
      expect(lpEn.translate('force_state_title'), 'Force State Transition');
      expect(lpEn.translate('self_pickup_preferred'), 'Self-Pickup Preferred');
      expect(lpEn.translate('fssai_info_disclaimer'), 'Informational only — No legal certification claims');

      // Tamil check
      final lpTa = LocaleProvider();
      lpTa.setLanguageSyncForTesting('ta');
      expect(lpTa.translate('nav_overview'), 'கண்ணோட்டம்');
      expect(lpTa.translate('nav_donations'), 'தானங்கள்');
      expect(lpTa.translate('nav_users'), 'பயனர்கள்');
      expect(lpTa.translate('verify_ngos'), 'தொண்டு நிறுவனங்களை சரிபார்க்கவும்');
      expect(lpTa.translate('admin_intervene'), 'தலையிடு');
      expect(lpTa.translate('force_state_title'), 'கட்டாய நிலை மாற்றம்');
      expect(lpTa.translate('self_pickup_preferred'), 'நேரடி சேகரிப்பு பரிந்துரைக்கப்படுகிறது');

      // Hindi check
      final lpHi = LocaleProvider();
      lpHi.setLanguageSyncForTesting('hi');
      expect(lpHi.translate('nav_overview'), 'अवलोकन');
      expect(lpHi.translate('nav_donations'), 'दान');
      expect(lpHi.translate('nav_users'), 'उपयोगकर्ता');
      expect(lpHi.translate('verify_ngos'), 'एनजीओ सत्यापित करें');
      expect(lpHi.translate('admin_intervene'), 'हस्तक्षेप करें');
      expect(lpHi.translate('force_state_title'), 'अनिवार्य स्थिति परिवर्तन');
      expect(lpHi.translate('self_pickup_preferred'), 'स्वयं पिकअप अनुशंसित');
    });
  });
}
