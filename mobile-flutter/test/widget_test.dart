import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:internet_dream/main.dart';

void main() {
  testWidgets('app shell renders navigation', (tester) async {
    await tester.pumpWidget(const DreamApp());
    await tester.pump();
    expect(find.text('Chat'), findsWidgets);
    expect(find.text('Sources'), findsWidgets);
    expect(find.byType(NavigationBar), findsOneWidget);
  });
}
