import 'dart:async';
import 'package:flutter/material.dart';
import '../models/server_status.dart';
import '../services/mqtt_service.dart';

/// Videos per playlist the Pi puts on the player (PLAYLIST_SYNC_LIMIT on the Pi).
const int playlistSyncLimit = 20;

class YouTubePlaylist {
  final String id;
  final String title;

  const YouTubePlaylist({required this.id, required this.title});
}

/// Shows which videos of a playlist go on the player: the newest
/// [playlistSyncLimit]. The Pi looks the playlist up on YouTube on request.
class YouTubeTab extends StatefulWidget {
  final YouTubePlaylist playlist;
  final MqttService mqttService;
  final bool connected;

  const YouTubeTab({
    super.key,
    required this.playlist,
    required this.mqttService,
    required this.connected,
  });

  @override
  State<YouTubeTab> createState() => _YouTubeTabState();
}

class _YouTubeTabState extends State<YouTubeTab> with AutomaticKeepAliveClientMixin {
  PlaylistInfo? _info;
  bool _loading = false;
  String? _error;
  Timer? _timeout;
  StreamSubscription<PlaylistInfo>? _subscription;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _subscription = widget.mqttService.playlistInfoResponse
        .where((info) => info.playlistId == widget.playlist.id)
        .listen(_onInfo);
    if (widget.connected) _request();
  }

  @override
  void didUpdateWidget(YouTubeTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.connected && !oldWidget.connected && _info == null && !_loading) {
      _request();
    }
  }

  @override
  void dispose() {
    _timeout?.cancel();
    _subscription?.cancel();
    super.dispose();
  }

  void _request() {
    if (!widget.mqttService.requestPlaylistInfo(widget.playlist.id)) {
      setState(() => _error = 'Not connected');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    _timeout?.cancel();
    // The Pi asks YouTube, which takes a few seconds; give up after a minute.
    _timeout = Timer(const Duration(seconds: 60), () {
      if (mounted && _loading) {
        setState(() {
          _loading = false;
          _error = 'No reply from the Pi. It may be offline.';
        });
      }
    });
  }

  void _onInfo(PlaylistInfo info) {
    _timeout?.cancel();
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (info.success) {
        _info = info;
        _error = null;
      } else {
        _error = info.error ?? 'The Pi could not read this playlist';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final info = _info;
    final newest = info == null
        ? const <PlaylistVideo>[]
        : info.videos.reversed.take(playlistSyncLimit).toList();
    final older = info == null ? 0 : info.videos.length - newest.length;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  info == null
                      ? widget.playlist.title
                      : 'Newest ${newest.length} of ${info.videos.length} go on the player',
                  style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                ),
              ),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(12),
                  child: SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                )
              else
                IconButton(
                  icon: const Icon(Icons.refresh, size: 20),
                  tooltip: 'Refresh',
                  onPressed: widget.connected ? _request : null,
                ),
            ],
          ),
        ),
        if (_error != null)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: Colors.amber.shade100,
            child: Text(_error!, style: const TextStyle(fontSize: 13)),
          ),
        Expanded(
          child: info == null
              ? Center(
                  child: Text(
                    _loading ? 'Asking the Pi for the playlist…' : 'Playlist not loaded',
                    style: TextStyle(color: Colors.grey.shade600),
                  ),
                )
              : ListView.separated(
                  itemCount: newest.length + (older > 0 ? 1 : 0),
                  separatorBuilder: (context, index) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    if (index == newest.length) {
                      return Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          '$older older video${older == 1 ? '' : 's'} not synced. '
                          'Add videos to the playlist on YouTube to update the player.',
                          style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                        ),
                      );
                    }
                    return ListTile(
                      dense: true,
                      leading: Text('${index + 1}', style: TextStyle(color: Colors.grey.shade600)),
                      title: Text(
                        newest[index].title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
