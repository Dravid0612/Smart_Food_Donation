import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/admin_operations_model.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/admin_provider.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/screens/admin/admin_dashboard.dart';

Widget createTestableAdminControlCenter({
  required AdminProvider adminProv,
}) {
  final authProv = AuthProvider();
  authProv.setCurrentUserForTesting(UserModel(
    id: 1,
    name: 'Ops Administrator',
    email: 'admin@smartfood.org',
    role: 'admin',
    phone: '+91 9876543210',
    address: 'HQ Ops Center',
    isActive: true,
  ));

  return MultiProvider(
    providers: [
      ChangeNotifierProvider(create: (_) => LocaleProvider()),
      ChangeNotifierProvider<AuthProvider>.value(value: authProv),
      ChangeNotifierProvider<AdminProvider>.value(value: adminProv),
    ],
    child: MaterialApp(
      theme: AppTheme.lightTheme,
      home: const AdminDashboardScreen(),
    ),
  );
}

void main() {
  group('Admin Control Center UX Redesign Tests', () {
    testWidgets('1. Header and compact operational summary strip render correctly', (tester) async {
      final adminProv = AdminProvider();
      final summary = AdminReceivingSummaryModel(
        activeRescues: 18,
        urgentRescues: 4,
        criticalRescues: 2,
        inTransit: 7,
        receivedToday: 350,
        distributedToday: 290,
        remainingToday: 60,
        issuesOpen: 2,
        foodAtRiskMeals: 180,
        completedToday: 12,
      );

      adminProv.setReceivingDataForTesting(summary: summary, items: []);

      await tester.pumpWidget(createTestableAdminControlCenter(adminProv: adminProv));
      await tester.pump();

      // Header checks
      expect(find.text('Administrator'), findsOneWidget);
      expect(find.text('Food Rescue Operations'), findsOneWidget);
      expect(find.byIcon(Icons.notifications_outlined), findsOneWidget);
      expect(find.byIcon(Icons.account_circle_outlined), findsOneWidget);

      // Compact operational summary strip values
      expect(find.text('18'), findsOneWidget);
      expect(find.text('Active'), findsWidgets);
      expect(find.text('4'), findsOneWidget);
      expect(find.text('Urgent'), findsWidgets);
      expect(find.text('2'), findsOneWidget);
      expect(find.text('At Risk'), findsOneWidget);
      expect(find.text('7'), findsOneWidget);
      expect(find.text('In Transit'), findsOneWidget);
    });

    testWidgets('2. Needs Attention section renders actionable problems and buttons', (tester) async {
      final adminProv = AdminProvider();
      final summary = AdminReceivingSummaryModel(
        activeRescues: 3,
        urgentRescues: 1,
        criticalRescues: 1,
        inTransit: 1,
        receivedToday: 100,
        distributedToday: 80,
        remainingToday: 20,
        issuesOpen: 1,
        foodAtRiskMeals: 50,
        completedToday: 5,
      );

      final criticalItem = AdminReceivingItemModel(
        id: 101,
        foodName: 'Steamed Rice & Dal',
        foodCategory: 'Cooked Food',
        quantity: 80,
        quantityUnit: 'Meals',
        donorId: 1,
        donorName: 'Grand Banquet',
        status: 'accepted',
        rescueUrgencyLevel: 'CRITICAL',
        remainingMinutes: 12,
        expectedQuantity: 80,
        pickupAddress: 'MG Road, Bengaluru',
        createdAt: '2026-08-24T10:00:00',
      );

      final mismatchItem = AdminReceivingItemModel(
        id: 102,
        foodName: 'Veg Biryani',
        foodCategory: 'Cooked Food',
        quantity: 100,
        quantityUnit: 'Meals',
        donorId: 2,
        status: 'delivered',
        rescueUrgencyLevel: 'FRESH',
        hasQuantityMismatch: true,
        expectedQuantity: 100,
        receivedQuantity: 92,
        ngoName: 'Hope Shelter',
        pickupAddress: 'Indiranagar, Bengaluru',
        createdAt: '2026-08-24T11:00:00',
      );

      adminProv.setReceivingDataForTesting(
        summary: summary,
        items: [criticalItem, mismatchItem],
      );

      await tester.pumpWidget(createTestableAdminControlCenter(adminProv: adminProv));
      await tester.pump();

      // Needs Attention section title & badge
      expect(find.text('Needs Attention'), findsOneWidget);
      expect(find.text('🔴 Critical Rescue'), findsOneWidget);
      expect(find.text('Steamed Rice & Dal • 80 Meals'), findsWidgets);
      expect(find.text('No volunteer assigned'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Intervene'), findsOneWidget);

      // Quantity mismatch card
      expect(find.text('🟠 Quantity Mismatch'), findsOneWidget);
      expect(find.text('Veg Biryani • 100 Meals'), findsWidgets);
      expect(find.text('100 expected • 92 received'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Review'), findsOneWidget);
    });

    testWidgets('3. All-clear state renders when no critical issues exist', (tester) async {
      final adminProv = AdminProvider();
      final summary = AdminReceivingSummaryModel(
        activeRescues: 5,
        urgentRescues: 0,
        criticalRescues: 0,
        inTransit: 2,
        receivedToday: 200,
        distributedToday: 200,
        remainingToday: 0,
        issuesOpen: 0,
        foodAtRiskMeals: 0,
        completedToday: 10,
      );

      final normalItem = AdminReceivingItemModel(
        id: 201,
        foodName: 'Curd Rice',
        foodCategory: 'Cooked Food',
        quantity: 40,
        quantityUnit: 'Meals',
        donorId: 1,
        status: 'completed',
        rescueUrgencyLevel: 'FRESH',
        remainingMinutes: 120,
        expectedQuantity: 40,
        receivedQuantity: 40,
        pickupAddress: 'Koramangala, Bengaluru',
        createdAt: '2026-08-24T12:00:00',
      );

      adminProv.setReceivingDataForTesting(
        summary: summary,
        items: [normalItem],
      );

      await tester.pumpWidget(createTestableAdminControlCenter(adminProv: adminProv));
      await tester.pump();

      expect(find.text('Operations are running normally'), findsOneWidget);
      expect(find.text('No critical rescues, delayed deliveries, or unresolved urgent issues'), findsOneWidget);
    });

    testWidgets('4. Food Receiving, NGO Capacity, and Quick Actions render', (tester) async {
      final adminProv = AdminProvider();
      final summary = AdminReceivingSummaryModel(
        activeRescues: 4,
        urgentRescues: 1,
        criticalRescues: 0,
        inTransit: 2,
        receivedToday: 350,
        distributedToday: 290,
        remainingToday: 60,
        issuesOpen: 0,
        foodAtRiskMeals: 180,
        completedToday: 15,
      );

      final capacities = [
        AdminNgoCapacityModel(
          id: 1,
          organizationName: 'Green Hope Foundation',
          address: 'Koramangala',
          currentCapacity: 90,
          maxCapacity: 500,
          remainingCapacity: 410,
          utilizationPercent: 18.0,
          isVerified: true,
          isOpen: true,
          statusColor: 'GREEN',
        ),
        AdminNgoCapacityModel(
          id: 2,
          organizationName: 'Hope Shelter',
          address: 'Indiranagar',
          currentCapacity: 330,
          maxCapacity: 500,
          remainingCapacity: 170,
          utilizationPercent: 66.0,
          isVerified: true,
          isOpen: true,
          statusColor: 'AMBER',
        ),
      ];

      adminProv.setReceivingDataForTesting(
        summary: summary,
        items: [],
        capacities: capacities,
      );

      await tester.pumpWidget(createTestableAdminControlCenter(adminProv: adminProv));
      await tester.pump();

      // Food Receiving Section
      expect(find.text('Food Receiving'), findsWidgets);
      expect(find.text('350 meals received today'), findsOneWidget);

      // NGO Capacity Section
      expect(find.text('NGO Capacity'), findsOneWidget);
      expect(find.text('Green Hope Foundation'), findsOneWidget);
      expect(find.text('82% remaining'), findsOneWidget);

      // Quick Actions Section
      expect(find.text('Quick Actions'), findsOneWidget);
      expect(find.text('Verify & Approve NGO'), findsOneWidget);

      // Bottom Nav Destinations
      expect(find.text('Rescues'), findsWidgets);
      expect(find.text('Issues'), findsWidgets);
      expect(find.text('Profile'), findsOneWidget);
    });
  });
}
