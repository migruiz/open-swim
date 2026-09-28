import 'package:flutter_test/flutter_test.dart';
import 'package:open_swim/models/server_status.dart';
import 'package:open_swim/services/update_service.dart';
import 'package:open_swim/widgets/status_card.dart';

void main() {
  group('DeviceStatus', () {
    test('parses the Pi statuses, including safe_to_unplug', () {
      final status = DeviceStatus.parse(
          '{"status": "safe_to_unplug", "device": "/dev/sda1", "timestamp": 1790600000.5}');

      expect(status.state, PlayerState.safeToUnplug);
      expect(status.at, DateTime.fromMillisecondsSinceEpoch(1790600000500));
      expect(DeviceStatus.parse('{"status": "connected"}').state, PlayerState.connected);
      expect(DeviceStatus.parse('{"status": "disconnected"}').state, PlayerState.disconnected);
    });

    test('unknown values and bad JSON become unknown instead of throwing', () {
      expect(DeviceStatus.parse('{"status": "something_new"}').state, PlayerState.unknown);
      expect(DeviceStatus.parse('not json').state, PlayerState.unknown);
    });
  });

  group('SyncProgress', () {
    const running = '{"stages": ['
        '{"name": "podcast_library", "label": "Download podcast episodes", "status": "completed", "error": null},'
        '{"name": "youtube_library", "label": "Download YouTube playlists", "status": "running", "error": null}'
        '], "timestamp": "2026-09-28T02:14:00Z"}';

    test('reports the running stage', () {
      final progress = SyncProgress.parse(running)!;

      expect(progress.isRunning, isTrue);
      expect(progress.current?.label, 'Download YouTube playlists');
      expect(progress.at, DateTime.utc(2026, 9, 28, 2, 14).toLocal());
    });

    test('reports errors of a finished sync', () {
      final progress = SyncProgress.parse('{"stages": ['
          '{"name": "youtube_library", "label": "Download YouTube playlists", "status": "error", "error": "HTTP 403"}'
          ']}')!;

      expect(progress.isRunning, isFalse);
      expect(progress.hasErrors, isTrue);
      expect(progress.stages.single.error, 'HTTP 403');
    });

    test('bad JSON is ignored', () {
      expect(SyncProgress.parse('nope'), isNull);
    });
  });

  test('PlaylistInfo parses a Pi reply', () {
    final info = PlaylistInfo.parse('{"success": true, "playlist_id": "PL1", "title": "newai",'
        ' "videos": [{"id": "v1", "title": "First"}, {"id": "v2", "title": "Second"}]}')!;

    expect(info.playlistId, 'PL1');
    expect(info.videos.map((v) => v.id), ['v1', 'v2']);
  });

  test('isNewerVersion compares numerically and tolerates suffixes', () {
    expect(UpdateService.isNewerVersion('1.1.0', '1.0.0'), isTrue);
    expect(UpdateService.isNewerVersion('1.0.10', '1.0.9'), isTrue);
    expect(UpdateService.isNewerVersion('1.1.0', '1.1.0'), isFalse);
    expect(UpdateService.isNewerVersion('1.0.2', '1.1.0'), isFalse);
    expect(UpdateService.isNewerVersion('1.2.0-beta', '1.1.0+5'), isTrue);
  });

  test('formatWhen', () {
    final now = DateTime(2026, 9, 28, 9, 0);
    expect(formatWhen(DateTime(2026, 9, 28, 2, 5), now: now), 'today 02:05');
    expect(formatWhen(DateTime(2026, 9, 27, 23, 59), now: now), 'yesterday 23:59');
    expect(formatWhen(DateTime(2026, 9, 20, 7, 0), now: now), '20/9 07:00');
  });
}
