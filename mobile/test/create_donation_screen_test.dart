import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_food_waste_donation/core/api/api_client.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/models/user_model.dart';
import 'package:smart_food_waste_donation/providers/auth_provider.dart';
import 'package:smart_food_waste_donation/providers/donation_provider.dart';
import 'package:smart_food_waste_donation/screens/donor/create_donation_screen.dart';

class MockAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    return ResponseBody.fromString('[]', 200, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    });
  }
  @override
  void close({bool force = false}) {}
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    ApiClient().dio.httpClientAdapter = MockAdapter();
  });

  testWidgets('Test CreateDonationScreen Step 0 and Step 1 layout and navigation buttons', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.75;
    addTearDown(() => tester.view.resetPhysicalSize());

    final localeProv = LocaleProvider();
    final authProv = AuthProvider();
    authProv.setCurrentUserForTesting(
      UserModel(
        id: 101,
        name: 'Grand Hotel Kitchen',
        email: 'donor@kitchen.org',
        phone: '+91 98765 43210',
        role: 'donor',
        isActive: true,
        address: '123 Anna Salai, Chennai',
        latitude: 13.0827,
        longitude: 80.2707,
      ),
    );
    final donProv = DonationProvider();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<LocaleProvider>.value(value: localeProv),
          ChangeNotifierProvider<AuthProvider>.value(value: authProv),
          ChangeNotifierProvider<DonationProvider>.value(value: donProv),
        ],
        child: MaterialApp(
          theme: AppTheme.light,
          home: const CreateDonationScreen(),
        ),
      ),
    );

    await tester.pump();

    // Verify continue buttons on Step 0
    final continueFinder = find.text('CONTINUE');
    expect(continueFinder, findsAtLeastNWidgets(1));

    // Tap the pinned continue button to advance to Step 1 (Quantity)
    await tester.tap(continueFinder.last);
    await tester.pump();

    // Verify on Step 1: Step progress shows Step 2 of 6 / QUANTITY
    expect(find.textContaining('QUANTITY'), findsAtLeastNWidgets(1));
    expect(find.text('2 / 6'), findsOneWidget);

    // Verify CONTINUE and BACK buttons exist on Step 1
    final continueStep1 = find.text('CONTINUE');
    expect(continueStep1, findsAtLeastNWidgets(1));

    final backStep1 = find.text('BACK');
    expect(backStep1, findsAtLeastNWidgets(1));

    // Tap BACK to return to Step 0
    await tester.tap(backStep1.first);
    await tester.pump();
    expect(find.text('1 / 6'), findsOneWidget);

    // Tap CONTINUE on Step 0 again
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();
    expect(find.text('2 / 6'), findsOneWidget);

    // Tap CONTINUE on Step 1 to go to Step 2 (Storage)
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();
    expect(find.text('3 / 6'), findsOneWidget);
    expect(find.text('CONTINUE'), findsAtLeastNWidgets(1));
    expect(find.text('BACK'), findsAtLeastNWidgets(1));

    // Tap CONTINUE on Step 2 to go to Step 3 (Photos)
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();
    expect(find.text('4 / 6'), findsOneWidget);
    expect(find.text('CONTINUE'), findsAtLeastNWidgets(1));
    expect(find.text('BACK'), findsAtLeastNWidgets(1));

    // Tap CONTINUE on Step 3 to go to Step 4 (Pickup)
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();
    expect(find.text('5 / 6'), findsOneWidget);
    expect(find.text('CONTINUE'), findsAtLeastNWidgets(1));
    expect(find.text('BACK'), findsAtLeastNWidgets(1));

    // Tap CONTINUE on Step 4 to go to Step 5 (Review)
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();
    expect(find.text('6 / 6'), findsOneWidget);
    expect(find.textContaining('CREATE FOOD DONATION'), findsAtLeastNWidgets(1));
    expect(find.text('BACK'), findsAtLeastNWidgets(1));

    // Drain pending network timers
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Test CreateDonationScreen on narrow device with 3-button navigation bar insets', (tester) async {
    // Exact screenshot dimensions (458 x 1024, DPR 2.75) with bottom navigation bar padding
    tester.view.physicalSize = const Size(458 * 2.75, 1024 * 2.75);
    tester.view.devicePixelRatio = 2.75;
    tester.view.padding = const FakeViewPadding(bottom: 132); // 48dp on 2.75x
    tester.view.viewPadding = const FakeViewPadding(bottom: 132);
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetPadding();
      tester.view.resetViewPadding();
    });

    final localeProv = LocaleProvider();
    final authProv = AuthProvider();
    authProv.setCurrentUserForTesting(
      UserModel(
        id: 101,
        name: 'Grand Hotel Kitchen',
        email: 'donor@kitchen.org',
        phone: '+91 98765 43210',
        role: 'donor',
        isActive: true,
        address: '123 Anna Salai, Chennai',
        latitude: 13.0827,
        longitude: 80.2707,
      ),
    );
    final donProv = DonationProvider();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<LocaleProvider>.value(value: localeProv),
          ChangeNotifierProvider<AuthProvider>.value(value: authProv),
          ChangeNotifierProvider<DonationProvider>.value(value: donProv),
        ],
        child: MaterialApp(
          theme: AppTheme.light,
          home: const CreateDonationScreen(),
        ),
      ),
    );

    await tester.pump();

    // Advance to Step 1 (the exact step in user screenshot)
    await tester.tap(find.text('CONTINUE').last);
    await tester.pump();

    expect(find.text('2 / 6'), findsOneWidget);
    expect(find.text('Flexible Quantity & Units'), findsOneWidget);

    // Both the inline and bottom navigation buttons must be present
    final continueButtons = find.text('CONTINUE');
    expect(continueButtons, findsAtLeastNWidgets(1));

    final backButtons = find.text('BACK');
    expect(backButtons, findsAtLeastNWidgets(1));

    // Both must be interactable without errors
    await tester.tap(continueButtons.last);
    await tester.pump();
    expect(find.text('3 / 6'), findsOneWidget);

    await tester.pump(const Duration(seconds: 1));
  });
}
