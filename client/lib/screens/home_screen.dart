import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';
import '../services/mqtt_service.dart';
import '../services/podcast_service.dart';
import '../services/update_service.dart';
import '../widgets/connection_status_bar.dart';
import '../widgets/podcast_tab.dart';
import '../widgets/youtube_tab.dart';

// Hardcoded YouTube playlists (temporary)
final _playlists = [
  const YouTubePlaylist(id: 'PLxx1', title: 'Playlist 1'),
  const YouTubePlaylist(id: 'PLxx2', title: 'Playlist 2'),
];

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final MqttService _mqttService = MqttService();
  final PodcastService _podcastService = PodcastService();
  final UpdateService _updateService = UpdateService();

  AppMqttConnectionState _connectionState = AppMqttConnectionState.disconnected;
  Set<String> _syncedEpisodeIds = {};

  // Update state
  UpdateInfo? _updateInfo;
  bool _isDownloading = false;
  double _downloadProgress = 0;

  StreamSubscription<AppMqttConnectionState>? _connectionStateSubscription;
  StreamSubscription<List<dynamic>>? _episodesToSyncSubscription;

  @override
  void initState() {
    super.initState();

    // Tabs: Podcast + YouTube playlists
    _tabController = TabController(
      length: 1 + _playlists.length,
      vsync: this,
    );

    // Listen to connection state changes
    _connectionStateSubscription = _mqttService.connectionState.listen((state) {
      setState(() {
        _connectionState = state;
      });

      // On connect, request current sync state
      if (state == AppMqttConnectionState.connected) {
        _mqttService.requestEpisodesToSync();
      }
    });

    // Listen to episodes-to-sync responses
    _episodesToSyncSubscription =
        _mqttService.episodesToSyncResponse.listen((episodes) {
      final ids = <String>{};
      for (final ep in episodes) {
        if (ep is Map<String, dynamic> && ep['id'] != null) {
          ids.add(ep['id'] as String);
        }
      }
      setState(() {
        _syncedEpisodeIds = ids;
      });
      _podcastService.applySelectedIds(ids);
    });

    // Initial connection
    _mqttService.connect();

    // Check for updates
    _checkForUpdates();
  }

  Future<void> _checkForUpdates() async {
    final updateInfo = await _updateService.checkForUpdate();
    if (updateInfo != null && mounted) {
      setState(() {
        _updateInfo = updateInfo;
      });
    }
  }

  Future<void> _downloadUpdate() async {
    if (_updateInfo == null || _isDownloading) return;

    setState(() {
      _isDownloading = true;
      _downloadProgress = 0;
    });

    await _updateService.downloadAndInstall(
      _updateInfo!.downloadUrl,
      onProgress: (progress) {
        if (mounted) {
          setState(() {
            _downloadProgress = progress;
          });
        }
      },
    );

    if (mounted) {
      setState(() {
        _isDownloading = false;
      });
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _connectionStateSubscription?.cancel();
    _episodesToSyncSubscription?.cancel();
    _mqttService.dispose();
    _podcastService.dispose();
    super.dispose();
  }

  void _onEpisodeToggled(PodcastEpisode episode) {
    // Toggle the selection
    final newSelected = !episode.isSelected;
    _podcastService.updateSelection(episode.id, newSelected);

    // Update the synced IDs
    setState(() {
      if (newSelected) {
        _syncedEpisodeIds.add(episode.id);
      } else {
        _syncedEpisodeIds.remove(episode.id);
      }
    });

    // Build and publish the new sync list
    _publishSyncList();
  }

  void _publishSyncList() {
    final selectedEpisodes = _podcastService.selectedEpisodes;
    final payload = json.encode(
      selectedEpisodes.map((e) => e.toSyncJson()).toList(),
    );
    _mqttService.publishMessage('openswim/episodes_to_sync', payload);
  }

  Widget _buildUpdateBanner() {
    if (_updateInfo == null) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      color: Colors.blue.shade100,
      child: Row(
        children: [
          const Icon(Icons.system_update, color: Colors.blue),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Update available: v${_updateInfo!.version}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                if (_isDownloading)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: LinearProgressIndicator(value: _downloadProgress),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (!_isDownloading)
            ElevatedButton(
              onPressed: _downloadUpdate,
              child: const Text('Update'),
            )
          else
            Text('${(_downloadProgress * 100).toInt()}%'),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Open Swim'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ConnectionStatusBar(
              connectionState: _connectionState,
              onReconnect: () => _mqttService.reconnect(),
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            const Tab(text: 'Podcast'),
            ..._playlists.map((p) => Tab(text: p.title)),
          ],
        ),
      ),
      body: Column(
        children: [
          _buildUpdateBanner(),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                PodcastTab(
                  podcastService: _podcastService,
                  syncedEpisodeIds: _syncedEpisodeIds,
                  onEpisodeToggled: _onEpisodeToggled,
                ),
                ..._playlists.map((p) => YouTubeTab(playlist: p)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
