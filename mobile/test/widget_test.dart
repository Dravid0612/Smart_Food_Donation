import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/main.dart';

void main() {
  testWidgets('Smart Food App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartFoodApp());
    expect(find.byType(SmartFoodApp), findsOneWidget);
    await tester.pump(const Duration(seconds: 3));
  });
}
