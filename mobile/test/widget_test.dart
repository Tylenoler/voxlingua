import 'package:flutter_test/flutter_test.dart';
import 'package:voxlingua_mobile/main.dart';

void main() {
  testWidgets('App should render', (WidgetTester tester) async {
    await tester.pumpWidget(const VoxLinguaApp());
    expect(find.text('VoxLingua'), findsOneWidget);
  });
}
