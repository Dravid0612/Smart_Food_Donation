import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/core/theme/app_theme.dart';
import 'package:smart_food_waste_donation/screens/auth/auth_error_banner.dart';

void main() {
  group('AuthErrorBanner Specification Tests', () {
    testWidgets('Renders error icon and plain-language message', (tester) async {
      const errorMessage = 'Invalid email or password. Please try again.';

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: const Scaffold(
            body: AuthErrorBanner(message: errorMessage),
          ),
        ),
      );

      // Verify text
      expect(find.text(errorMessage), findsOneWidget);

      // Verify icon
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      final iconWidget = tester.widget<Icon>(find.byIcon(Icons.error_outline));
      expect(iconWidget.color, AppColors.chili);
      expect(iconWidget.size, 18);
    });

    testWidgets('Has liveRegion enabled in Semantics for screen-reader accessibility', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: const Scaffold(
            body: AuthErrorBanner(message: 'Account not verified'),
          ),
        ),
      );

      final semanticsFinder = find.byWidgetPredicate(
        (widget) => widget is Semantics && widget.properties.liveRegion == true,
      );
      expect(semanticsFinder, findsOneWidget);
    });
  });
}
