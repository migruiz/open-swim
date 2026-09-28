import 'dart:convert';

/// The player's state as last reported by the Pi on `openswim/device/status`.
enum PlayerState { connected, safeToUnplug, disconnected, unknown }

class DeviceStatus {
  final PlayerState state;
  final DateTime? at;

  const DeviceStatus(this.state, this.at);

  static const unknown = DeviceStatus(PlayerState.unknown, null);

  /// Tolerant parse: an unrecognised status becomes [PlayerState.unknown]
  /// rather than throwing, so a new server value can't break the app.
  factory DeviceStatus.parse(String payload) {
    try {
      final data = json.decode(payload) as Map<String, dynamic>;
      final state = switch (data['status']) {
        'connected' => PlayerState.connected,
        'safe_to_unplug' => PlayerState.safeToUnplug,
        'disconnected' => PlayerState.disconnected,
        _ => PlayerState.unknown,
      };
      final ts = data['timestamp'];
      final at = ts is num
          ? DateTime.fromMillisecondsSinceEpoch((ts * 1000).round())
          : null;
      return DeviceStatus(state, at);
    } catch (_) {
      return unknown;
    }
  }
}

enum StageState { pending, running, completed, error }

class SyncStageInfo {
  final String name;
  final String label;
  final StageState state;
  final String? error;

  const SyncStageInfo({
    required this.name,
    required this.label,
    required this.state,
    this.error,
  });
}

/// The latest `openswim/sync/progress` message: the stages of the current or
/// most recent sync.
class SyncProgress {
  final List<SyncStageInfo> stages;
  final DateTime? at;

  const SyncProgress(this.stages, this.at);

  bool get isRunning => stages.any((s) => s.state == StageState.running);
  bool get hasErrors => stages.any((s) => s.state == StageState.error);

  /// The stage in progress, or the last one reached.
  SyncStageInfo? get current {
    for (final stage in stages) {
      if (stage.state == StageState.running) return stage;
    }
    return stages.isEmpty ? null : stages.last;
  }

  static SyncProgress? parse(String payload) {
    try {
      final data = json.decode(payload) as Map<String, dynamic>;
      final stages = (data['stages'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map((s) => SyncStageInfo(
                name: s['name'] as String? ?? '',
                label: s['label'] as String? ?? s['name'] as String? ?? '',
                state: switch (s['status']) {
                  'running' => StageState.running,
                  'completed' => StageState.completed,
                  'error' => StageState.error,
                  _ => StageState.pending,
                },
                error: s['error'] as String?,
              ))
          .toList();
      final at = DateTime.tryParse(data['timestamp'] as String? ?? '')?.toLocal();
      return SyncProgress(stages, at);
    } catch (_) {
      return null;
    }
  }
}

class PlaylistVideo {
  final String id;
  final String title;

  const PlaylistVideo(this.id, this.title);
}

/// A reply on `openswim/playlist-info/response`.
class PlaylistInfo {
  final String? playlistId;
  final bool success;
  final String? title;

  /// In YouTube's order: oldest added first.
  final List<PlaylistVideo> videos;
  final String? error;

  const PlaylistInfo({
    required this.playlistId,
    required this.success,
    this.title,
    this.videos = const [],
    this.error,
  });

  static PlaylistInfo? parse(String payload) {
    try {
      final data = json.decode(payload) as Map<String, dynamic>;
      return PlaylistInfo(
        playlistId: data['playlist_id'] as String?,
        success: data['success'] == true,
        title: data['title'] as String?,
        videos: (data['videos'] as List<dynamic>? ?? [])
            .whereType<Map<String, dynamic>>()
            .map((v) => PlaylistVideo(v['id'] as String? ?? '', v['title'] as String? ?? ''))
            .toList(),
        error: data['error'] as String?,
      );
    } catch (_) {
      return null;
    }
  }
}
