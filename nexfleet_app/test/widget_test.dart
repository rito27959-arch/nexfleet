import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:nexfleet_app/main.dart';

void main() {
  testWidgets('NexFleetApp se lance', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const NexFleetApp());
    await tester.pump();
    expect(find.byType(NexFleetApp), findsOneWidget);
  });
}