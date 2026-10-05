import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/widgets/auth/app_text_field.dart';

void main() {
  setUp(() {
    AppLocale.setLocale('en');
  });

  group('AppTextField Widget Specification Tests', () {
    testWidgets('Renders label, hint, and text field correctly', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: AppTextField(
              label: 'Email Address',
              hint: 'you@example.com',
              controller: controller,
            ),
          ),
        ),
      );

      expect(find.text('Email Address'), findsOneWidget);
      expect(find.text('you@example.com'), findsOneWidget);
      expect(find.byType(TextFormField), findsOneWidget);

      // Verify no password toggle for regular text field
      expect(find.byType(IconButton), findsNothing);

      // Enter text
      await tester.enterText(find.byType(TextFormField), 'donor@test.org');
      expect(controller.text, 'donor@test.org');
    });

    testWidgets('Password field toggles obscurity and icon on button tap', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: AppTextField(
              label: 'Password',
              hint: 'Enter your password',
              controller: controller,
              obscureText: true,
              semanticLabel: 'Secure password input',
            ),
          ),
        ),
      );

      // Initially obscured
      final editableTextFinder = find.byType(EditableText);
      EditableText editableText = tester.widget<EditableText>(editableTextFinder);
      expect(editableText.obscureText, isTrue);

      // Suffix toggle button exists with localized English tooltip
      final toggleBtnFinder = find.byType(IconButton);
      expect(toggleBtnFinder, findsOneWidget);
      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
      IconButton iconBtn = tester.widget<IconButton>(toggleBtnFinder);
      expect(iconBtn.tooltip, 'Show password');

      // Tap toggle button to show password
      await tester.tap(toggleBtnFinder);
      await tester.pumpAndSettle();

      editableText = tester.widget<EditableText>(editableTextFinder);
      expect(editableText.obscureText, isFalse);
      expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
      iconBtn = tester.widget<IconButton>(toggleBtnFinder);
      expect(iconBtn.tooltip, 'Hide password');

      // Tap again to re-obscure
      await tester.tap(toggleBtnFinder);
      await tester.pumpAndSettle();

      editableText = tester.widget<EditableText>(editableTextFinder);
      expect(editableText.obscureText, isTrue);
      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
      iconBtn = tester.widget<IconButton>(toggleBtnFinder);
      expect(iconBtn.tooltip, 'Show password');
    });

    testWidgets('Password toggle tooltips reflect active locale (Tamil and Hindi)', (tester) async {
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      // Tamil test
      AppLocale.setLocale('ta');
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: AppTextField(
              label: 'கடவுச்சொல்',
              hint: '••••••••',
              controller: controller,
              obscureText: true,
            ),
          ),
        ),
      );

      IconButton btn = tester.widget<IconButton>(find.byType(IconButton));
      expect(btn.tooltip, 'கடவுச்சொல்லைக் காட்டு');

      // Hindi test
      AppLocale.setLocale('hi');
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: AppTextField(
              label: 'पासवर्ड',
              hint: '••••••••',
              controller: controller,
              obscureText: true,
            ),
          ),
        ),
      );

      btn = tester.widget<IconButton>(find.byType(IconButton));
      expect(btn.tooltip, 'पासवर्ड दिखाएं');
    });

    testWidgets('Validator is invoked on form validation', (tester) async {
      final formKey = GlobalKey<FormState>();
      final controller = TextEditingController();
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: Form(
              key: formKey,
              child: AppTextField(
                label: 'Phone',
                hint: '+91 9876543210',
                controller: controller,
                validator: (val) {
                  if (val == null || val.isEmpty) {
                    return 'Phone number is required';
                  }
                  return null;
                },
              ),
            ),
          ),
        ),
      );

      // Validate empty form
      final isValid = formKey.currentState!.validate();
      await tester.pumpAndSettle();

      expect(isValid, isFalse);
      expect(find.text('Phone number is required'), findsOneWidget);

      // Enter valid input
      await tester.enterText(find.byType(TextFormField), '+91 9800000001');
      final isNowValid = formKey.currentState!.validate();
      await tester.pumpAndSettle();

      expect(isNowValid, isTrue);
      expect(find.text('Phone number is required'), findsNothing);
    });
  });
}
