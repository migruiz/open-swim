import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:open_swim/services/podcast_service.dart';
import 'package:open_swim/state/selection_controller.dart';
import 'package:open_swim/widgets/podcast_tab.dart';

void main() {
  Future<SelectionController> pumpTab(
    WidgetTester tester, {
    required bool connected,
    required VoidCallback onSubmit,
  }) async {
    final selection = SelectionController();
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: PodcastTab(
          // The feed request fails under flutter_test (HTTP 400); the tab
          // still lists the Pi's picks.
          podcastService: PodcastService(),
          selection: selection,
          connected: connected,
          onRefresh: () {},
          onSubmit: onSubmit,
        ),
      ),
    ));
    await tester.pumpAndSettle();
    return selection;
  }

  testWidgets('picks are locked until the Pi list arrives, then Submit sends edits',
      (tester) async {
    var submits = 0;
    final selection = await pumpTab(tester, connected: true, onSubmit: () => submits++);

    expect(find.textContaining('Loading your picks from the Pi'), findsOneWidget);

    selection.applyServerList([
      {
        'id': 'a',
        'date': '2026-05-11T15:03:10.000Z',
        'title': 'Billy Madison Show - May 11',
        'download_url': 'https://example.com/a.mp3',
      },
    ]);
    await tester.pump();

    expect(find.textContaining('Loading your picks'), findsNothing);
    expect(find.text('PICKED FOR THE PLAYER (1)'), findsOneWidget);
    expect(find.text('Submit'), findsNothing);

    await tester.tap(find.byType(Checkbox).first);
    await tester.pump();

    expect(find.text('1 unsent change'), findsOneWidget);
    await tester.tap(find.text('Submit'));
    expect(submits, 1);
  });

  testWidgets('Submit is disabled while disconnected', (tester) async {
    var submits = 0;
    final selection = await pumpTab(tester, connected: false, onSubmit: () => submits++);
    selection.applyServerList([
      {'id': 'a', 'date': '2026-05-11T15:03:10.000Z', 'title': 'A', 'download_url': 'u'},
    ]);
    await tester.pump();
    selection.toggle('a');
    await tester.pump();

    expect(find.textContaining('(not connected)'), findsOneWidget);
    await tester.tap(find.text('Submit'));
    expect(submits, 0);
  });
}
