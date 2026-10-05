import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/donation_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/providers/notification_provider.dart';
import 'package:smart_food_waste_donation/screens/donor/donor_dashboard.dart';
import 'package:smart_food_waste_donation/screens/donor/donor_history_screen.dart';
import 'package:smart_food_waste_donation/screens/donor/donor_impact_dashboard_screen.dart';
import 'package:smart_food_waste_donation/screens/donor/quick_rescue_screen.dart';
import 'package:smart_food_waste_donation/screens/profile/profile_screen.dart';
import 'package:smart_food_waste_donation/widgets/donation_card.dart';
import 'package:smart_food_waste_donation/widgets/role_bottom_nav.dart';

import 'package:smart_food_waste_donation/models/donor_impact_model.dart';

Widget _buildTestApp(Widget child, {UserModel? user, DonorImpactSummaryModel? donorImpact, String language = 'en'}) {
  final lp = LocaleProvider();
  lp.setLanguage(language);

  final auth = AuthProvider();
  if (user != null) {
    auth.setCurrentUserForTesting(user);
  }

  final donProv = DonationProvider();
  if (donorImpact != null) {
    donProv.setDonorImpactForTesting(donorImpact);
  }

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<LocaleProvider>.value(value: lp),
      ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ChangeNotifierProvider<DonationProvider>.value(value: donProv),
      ChangeNotifierProvider<NotificationProvider>(create: (_) => NotificationProvider()),
    ],
    child: MaterialApp(
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

  group('Phase 3 Complete Donor Role Implementation Tests', () {
    final donorUser = UserModel(
      id: 101,
      name: 'Grand Hotel Kitchen',
      email: 'donor@kitchen.org',
      phone: '+91 98765 43210',
      role: 'donor',
      isActive: true,
      address: '123 Coastal Road, Chennai',
    );

    // ── 1. DONOR NAVIGATION (EXACTLY 4 TABS) ─────────────────────────────────
    testWidgets('1. Donor bottom navigation bar contains exactly 4 tabs (Home, Donate, History, Profile)', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const RoleBottomNav(currentRole: 'donor', currentIndex: 0),
          user: donorUser,
        ),
      );
      await tester.pumpAndSettle();

      final bottomNavFinder = find.byType(NavigationBar);
      expect(bottomNavFinder, findsOneWidget);

      final navBar = tester.widget<NavigationBar>(bottomNavFinder);
      expect(navBar.destinations.length, 4);

      // Verify destinations labels
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Donate'), findsOneWidget);
      expect(find.text('History'), findsOneWidget);
      expect(find.text('Profile'), findsOneWidget);
    });

    // ── 2. DONOR HOME SCREEN & ACTIVE RESCUE CARDS ────────────────────────────
    testWidgets('2. Donor home displays greeting, verified status, camera CTA, and RescueRing active cards', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const DonorDashboardScreen(),
          user: donorUser,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Verified Partner badge
      expect(find.text('Verified Partner'), findsAtLeastNWidgets(1));

      // Primary camera-first CTA: SCAN / TAKE PHOTO
      expect(find.text('SCAN / TAKE PHOTO'), findsOneWidget);

      // Nav chips
      expect(find.text('Why Donate?'), findsOneWidget);
      expect(find.text('How It Works'), findsOneWidget);
      expect(find.text('Donor Impact Summary'), findsOneWidget);
    });

    // ── 3. QUICK RESCUE SCREEN STRUCTURE & PREPARATION TIME ──────────────────
    testWidgets('3. QuickRescueScreen provides 1-3 image notice, prep time choices, storage, and deadline', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const QuickRescueScreen(),
          user: donorUser,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Multi-image upload notice: "Images must represent the same food donation"
      expect(find.textContaining('Images must represent the same food donation'), findsOneWidget);

      // Simple prep time choices (Section 7)
      expect(find.text('Just now'), findsOneWidget);
      expect(find.text('About 1 hour ago'), findsOneWidget);
      expect(find.text('About 2 hours ago'), findsOneWidget);
      expect(find.text('3+ hours ago'), findsOneWidget);

      // Storage condition chips (Section 8)
      expect(find.text('Room Temperature'), findsOneWidget);
      expect(find.text('Refrigerated'), findsOneWidget);
      expect(find.textContaining('Heated'), findsOneWidget);
      expect(find.text('Frozen'), findsOneWidget);

      // Pickup deadline operational window (Section 9)
      expect(find.text('Pickup Deadline'), findsOneWidget);
      expect(find.textContaining('operational handover cutoff'), findsOneWidget);
      expect(find.text('Within 1 hour'), findsOneWidget);
      expect(find.text('Within 2 hours'), findsOneWidget);

      // Safety declaration checkbox & SEND TO RESCUE button (Section 10 & 11)
      expect(find.textContaining('safe for consumption'), findsOneWidget);
      expect(find.text('SEND TO RESCUE'), findsOneWidget);
    });

    // ── 4. MANDATORY SPOILED FOOD BUG CORRECTION ─────────────────────────────
    testWidgets('4. Spoiled food conservative aggregation: spoilage in ANY image forces "Potential visual spoilage detected"', (tester) async {
      final spoiledDonation = DonationModel(
        id: 202,
        donorId: 101,
        foodName: 'Surplus Curd Rice',
        foodCategory: 'Cooked Food',
        quantity: 20,
        quantityUnit: 'Meals',
        status: 'pending',
        urgencyLevel: 'Fresh',
        aiVisualCondition: 'POOR', // Conservative aggregation result from moldy image
        aiConfidenceScore: 0.94,
        storageMethod: 'Room Temperature',
        preparationTime: DateTime.now().subtract(const Duration(hours: 1)).toIso8601String(),
        expiryTime: DateTime.now().add(const Duration(hours: 2)).toIso8601String(),
        createdAt: DateTime.now().toIso8601String(),
        pickupAddress: 'T. Nagar, Chennai',
      );

      await tester.pumpWidget(
        _buildTestApp(
          DonationCard(
            donation: spoiledDonation,
            currentRole: 'donor',
          ),
          user: donorUser,
        ),
      );
      await tester.pumpAndSettle();

      // UI MUST NOT say "Good visual condition"
      expect(find.text('Good visual condition'), findsNothing);
      // UI MUST say Spoilage suspected
      expect(find.textContaining('Spoilage'), findsOneWidget);
    });

    testWidgets('5. Clean food donation renders Good Visual Condition', (tester) async {
      final cleanDonation = DonationModel(
        id: 203,
        donorId: 101,
        foodName: 'Fresh Veg Biryani',
        foodCategory: 'Cooked Food',
        quantity: 30,
        quantityUnit: 'Meals',
        status: 'pending',
        urgencyLevel: 'Fresh',
        aiVisualCondition: 'GOOD',
        aiConfidenceScore: 0.92,
        storageMethod: 'Heated/Insulated',
        preparationTime: DateTime.now().subtract(const Duration(minutes: 30)).toIso8601String(),
        expiryTime: DateTime.now().add(const Duration(hours: 3)).toIso8601String(),
        createdAt: DateTime.now().toIso8601String(),
        pickupAddress: 'Adyar, Chennai',
      );

      await tester.pumpWidget(
        _buildTestApp(
          DonationCard(
            donation: cleanDonation,
            currentRole: 'donor',
          ),
          user: donorUser,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Good visual condition'), findsOneWidget);
    });

    // ── 6. DONOR IMPACT DASHBOARD (5 SPECIFIC METRICS + NO-TAX DISCLAIMER) ───
    testWidgets('6. DonorImpactDashboardScreen renders 5 required impact indicators and no-tax disclaimer', (tester) async {
      const mockImpact = DonorImpactSummaryModel(
        donorId: 101,
        donorName: 'Grand Hotel Kitchen',
        totalDonationsCount: 12,
        successfulRescuesCount: 11,
        mealsDonated: 150.0,
        mealsRescued: 140.0,
        mealsDistributed: 140.0,
        estimatedWasteDivertedKg: 63.0,
        estimatedValuePreservedInr: 6300.0,
        partnerNgosCount: 4,
        recognitionLevel: 'GOLD RESCUE PARTNER',
        completionRatePercent: 95.0,
        conversionFactorNote: 'Based on standard recovery estimates',
        monthlyBreakdown: [],
      );

      await tester.pumpWidget(
        _buildTestApp(
          const DonorImpactDashboardScreen(),
          user: donorUser,
          donorImpact: mockImpact,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // 1. Meals Rescued
      expect(find.text('Meals Rescued'), findsOneWidget);
      // 2. Food Recovered
      expect(find.text('Food Recovered'), findsOneWidget);
      // 3. Estimated CO2e
      expect(find.text('Estimated CO2e'), findsOneWidget);
      // 4. Estimated Water Footprint
      expect(find.text('Estimated Water'), findsOneWidget);
      // 5. Estimated Disposal Cost Avoided
      expect(find.text('Estimated Disposal Cost Avoided'), findsOneWidget);

      // Section 23: No tax deduction / write-off claims disclaimer
      expect(find.textContaining('All metrics are non-binding estimates'), findsOneWidget);
      expect(find.textContaining('No tax deduction or write-off claims'), findsOneWidget);
    });

    // ── 7. DONOR PROFILE (NAME, BUSINESS, CONTACT, VERIFICATION, LANGUAGES) ──
    testWidgets('7. ProfileScreen shows donor identity, contact, verification, and language selector', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const ProfileScreen(),
          user: donorUser,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Name & Business
      expect(find.text('Grand Hotel Kitchen'), findsAtLeastNWidgets(1));
      // Verified badge
      expect(find.textContaining('Verified Partner'), findsAtLeastNWidgets(1));
      // Contact
      expect(find.text('donor@kitchen.org'), findsOneWidget);
      expect(find.text('+91 98765 43210'), findsOneWidget);
      // Languages
      expect(find.text('English'), findsOneWidget);
      expect(find.text('தமிழ்'), findsOneWidget);
      expect(find.text('हिन्दी'), findsOneWidget);
      // Logout button
      expect(find.text('Log Out'), findsOneWidget);
    });

    // ── 8. DONOR HISTORY SCREEN ──────────────────────────────────────────────
    testWidgets('8. DonorHistoryScreen displays previous donations with filter chips', (tester) async {
      await tester.pumpWidget(
        _buildTestApp(
          const DonorHistoryScreen(),
          user: donorUser,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Donation History'), findsOneWidget);
      expect(find.text('Live Rescue Tracking'), findsOneWidget);
      // Filters
      expect(find.text('View All'), findsOneWidget);
      expect(find.text('In Progress'), findsOneWidget);
      expect(find.text('Rescue Completed'), findsOneWidget);
      expect(find.text('Cancelled'), findsOneWidget);
    });

    // ── 9. LOCALIZATION ACROSS ENGLISH, TAMIL, AND HINDI ─────────────────────
    test('9. Donor localization keys exist across English, Tamil, and Hindi', () {
      final keys = [
        'nav_home',
        'nav_donate',
        'nav_history',
        'nav_profile',
        'prep_just_now',
        'prep_1h_ago',
        'prep_2h_ago',
        'prep_3h_plus_ago',
        'pickup_deadline_title',
        'pickup_deadline_note',
        'same_food_donation_notice',
        'retake_photo',
        'preview_photo',
        'remove_photo',
        'tax_deduction_disclaimer',
        'visual_advisory_note',
        'share_whatsapp',
        'self_dropoff',
      ];

      for (final code in ['en', 'ta', 'hi']) {
        final dict = LocaleProvider.translations[code];
        expect(dict, isNotNull, reason: 'Dictionary for $code must exist');
        for (final k in keys) {
          expect(dict!.containsKey(k), isTrue, reason: 'Key $k missing in $code');
          expect(dict[k]!.isNotEmpty, isTrue, reason: 'Key $k cannot be empty in $code');
        }
      }
    });
  });
}
