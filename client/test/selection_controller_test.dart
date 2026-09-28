import 'package:flutter_test/flutter_test.dart';
import 'package:open_swim/models/podcast_episode.dart';
import 'package:open_swim/state/selection_controller.dart';

Map<String, dynamic> serverEntry(String id, {String date = '2026-05-11T15:03:10.000Z'}) => {
      'id': id,
      'date': date,
      'title': 'Episode $id',
      'download_url': 'https://example.com/$id.mp3',
    };

PodcastEpisode feedEpisode(String id, DateTime published) => PodcastEpisode(
      id: id,
      title: 'Feed $id',
      published: published,
      durationSeconds: 3600,
      mediaUrl: 'https://feed.example.com/$id.mp3',
    );

void main() {
  group('SelectionController', () {
    test('ignores taps until the Pi list has arrived', () {
      final selection = SelectionController();

      selection.toggle('a');

      expect(selection.loaded, isFalse);
      expect(selection.isSelected('a'), isFalse);
      expect(selection.hasChanges, isFalse);
    });

    test('mirrors the Pi list and counts local edits as changes', () {
      final selection = SelectionController()
        ..applyServerList([serverEntry('a'), serverEntry('b')]);

      expect(selection.draftIds, {'a', 'b'});
      expect(selection.hasChanges, isFalse);

      selection
        ..toggle('b')
        ..toggle('c');

      expect(selection.draftIds, {'a', 'c'});
      expect(selection.changeCount, 2);

      selection.discardChanges();
      expect(selection.draftIds, {'a', 'b'});
    });

    test('a reply arriving while editing does not overwrite the edits', () {
      final selection = SelectionController()..applyServerList([serverEntry('a')]);
      selection.toggle('b');

      selection.applyServerList([serverEntry('a')]);

      expect(selection.draftIds, {'a', 'b'});
    });

    test('reloading the feed never clears picks', () {
      // The old app stored picks on feed episodes, so a feed reload after the
      // Pi's list arrived showed everything unticked and the next tap sent a
      // one-episode list. Picks now live only in the controller.
      final selection = SelectionController()..applyServerList([serverEntry('a')]);
      final freshFeed = [feedEpisode('a', DateTime.utc(2026, 5, 11))];

      expect(selection.isSelected('a'), isTrue);
      expect(selection.payload(freshFeed).map((e) => e.id), ['a']);
    });

    test('payload keeps picks that are no longer in the feed', () {
      final selection = SelectionController()
        ..applyServerList([serverEntry('old', date: '2025-01-01T00:00:00.000Z')]);
      selection.toggle('new');

      final payload = selection.payload([feedEpisode('new', DateTime.utc(2026, 9, 1))]);

      expect(payload.map((e) => e.id), ['old', 'new']); // oldest first
      expect(payload.first.mediaUrl, 'https://example.com/old.mp3');
      expect(payload.last.mediaUrl, 'https://feed.example.com/new.mp3');
    });

    test('a matching reply confirms a submit', () {
      final selection = SelectionController()..applyServerList([serverEntry('a')]);
      selection
        ..toggle('b')
        ..submitted();

      // A stale reply that doesn't match yet keeps waiting and keeps the edits.
      expect(selection.applyServerList([serverEntry('a')]), isFalse);
      expect(selection.awaitingConfirmation, isTrue);
      expect(selection.draftIds, {'a', 'b'});

      expect(selection.applyServerList([serverEntry('a'), serverEntry('b')]), isTrue);
      expect(selection.awaitingConfirmation, isFalse);
      expect(selection.hasChanges, isFalse);
    });

    test('a timed-out submit keeps the edits for resending', () {
      final selection = SelectionController()..applyServerList([serverEntry('a')]);
      selection
        ..toggle('b')
        ..submitted()
        ..confirmationTimedOut();

      expect(selection.awaitingConfirmation, isFalse);
      expect(selection.hasChanges, isTrue);
      expect(selection.draftIds, {'a', 'b'});
    });
  });
}
