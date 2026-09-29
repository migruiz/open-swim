import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:open_swim/models/server_status.dart';
import 'package:open_swim/widgets/status_card.dart';

void main() {
  Future<void> pump(WidgetTester tester, VoidCallback? onSyncNow) {
    return tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: StatusCard(device: DeviceStatus.unknown, onSyncNow: onSyncNow),
      ),
    ));
  }

  testWidgets('Sync now calls back when enabled', (tester) async {
    var taps = 0;
    await pump(tester, () => taps++);

    await tester.tap(find.byTooltip('Sync now'));

    expect(taps, 1);
  });

  testWidgets('Sync now is disabled without a callback (disconnected)', (tester) async {
    await pump(tester, null);

    final button = tester.widget<IconButton>(find.byType(IconButton));
    expect(button.onPressed, isNull);
  });
}
