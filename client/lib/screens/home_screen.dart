import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/server_status.dart';
import '../services/mqtt_service.dart';
import '../services/podcast_service.dart';
import '../services/update_service.dart';
import '../state/selection_controller.dart';
import '../widgets/connection_status_bar.dart';
import '../widgets/podcast_tab.dart';
import '../widgets/status_card.dart';
import '../widgets/youtube_tab.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  late TabController _tabController;
  final MqttService _mqttService = MqttService();
  final PodcastService _podcastService = PodcastService();
  final UpdateService _updateService = UpdateService();
  final SelectionController _selection = SelectionController();

  AppMqttConnectionState _connectionState = AppMqttConnectionState.disconnected;
  DateTime? _lastRefreshed;
  DeviceStatus _deviceStatus = DeviceStatus.unknown;
  SyncProgress? _syncProgress;
  Timer? _confirmTimeout;

  // Update state
  UpdateInfo? _updateInfo;
  bool _isDownloading = false;
  double _downloadProgress = 0;

  // Playlists the Pi syncs
  List<YouTubePlaylist> _playlists = [];

  final List<StreamSubscription<dynamic>> _subscriptions = [];

  bool get _connected => _connectionState == AppMqttConnectionState.connected;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _tabController = TabController(length: 1 + _playlists.length, vsync: this);

    _subscriptions.addAll([
      _mqttService.connectionState.listen((state) {
        setState(() => _connectionState = state);
        if (state == AppMqttConnectionState.connected) _requestServerState();
      }),
      _mqttService.playlistsToSyncResponse.listen(_onPlaylists),
      _mqttService.episodesToSyncResponse.listen(_onEpisodesToSync),
      _mqttService.deviceStatus.listen((status) {
        if (mounted) setState(() => _deviceStatus = status);
      }),
      _mqttService.syncProgress.listen((progress) {
        if (mounted) setState(() => _syncProgress = progress);
      }),
      _podcastService.lastRefreshedStream.listen((timestamp) {
        if (mounted) setState(() => _lastRefreshed = timestamp);
      }),
    ]);

    _podcastService.loadFromCache().then((_) {
      if (mounted) setState(() => _lastRefreshed = _podcastService.lastRefreshed);
    });

    _mqttService.connect();
    _checkForUpdates();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) return;
    // Back from the background: the socket may have died silently, and the
    // Pi's state may have moved on overnight.
    if (_mqttService.isConnected) {
      _requestServerState();
    } else {
      _mqttService.reconnect();
    }
  }

  void _requestServerState() {
    _mqttService.requestEpisodesToSync();
    _mqttService.requestPlaylistsToSync();
  }

  void _onEpisodesToSync(List<dynamic> episodes) {
    final confirmed = _selection.applyServerList(episodes);
    if (confirmed) {
      _confirmTimeout?.cancel();
      _showSnack('Saved on the Pi. It starts downloading shortly.');
    }
  }

  void _onPlaylists(List<dynamic> playlists) {
    final newPlaylists = <YouTubePlaylist>[
      for (final pl in playlists)
        if (pl is Map<String, dynamic> && pl['id'] is String && pl['title'] is String)
          YouTubePlaylist(id: pl['id'] as String, title: pl['title'] as String),
    ];
    _updatePlaylists(newPlaylists);
  }

  void _submit() {
    final payload = json.encode(
      _selection.payload(_podcastService.cachedEpisodes).map((e) => e.toSyncJson()).toList(),
    );
    if (!_mqttService.publishMessage(Topics.episodesToSync, payload)) {
      _showSnack('Not connected. Nothing was sent.');
      return;
    }
    _selection.submitted();
    // Ask for the saved list back; its arrival confirms the Pi got the picks.
    _mqttService.requestEpisodesToSync();
    _confirmTimeout?.cancel();
    _confirmTimeout = Timer(const Duration(seconds: 15), () {
      if (!_selection.awaitingConfirmation) return;
      _selection.confirmationTimedOut();
      _showSnack('The Pi did not confirm. It may be offline; your changes are kept, try again later.');
    });
  }

  void _syncNow() {
    if (_mqttService.requestSync()) {
      _showSnack('Sync requested. The Pi starts within seconds, or right after the current sync.');
    } else {
      _showSnack('Not connected. Nothing was sent.');
    }
  }

  void _showSnack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _checkForUpdates() async {
    final updateInfo = await _updateService.checkForUpdate();
    if (updateInfo != null && mounted) {
      setState(() => _updateInfo = updateInfo);
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
        if (mounted) setState(() => _downloadProgress = progress);
      },
    );

    if (mounted) setState(() => _isDownloading = false);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _confirmTimeout?.cancel();
    for (final s in _subscriptions) {
      s.cancel();
    }
    _tabController.dispose();
    _mqttService.dispose();
    _podcastService.dispose();
    _selection.dispose();
    super.dispose();
  }

  void _updatePlaylists(List<YouTubePlaylist> newPlaylists) {
    if (!mounted) return;

    final oldIds = _playlists.map((p) => p.id).toList();
    final newIds = newPlaylists.map((p) => p.id).toList();
    if (oldIds.length == newIds.length && oldIds.every(newIds.contains)) return;

    final oldController = _tabController;
    final oldIndex = oldController.index;

    setState(() {
      _playlists = newPlaylists;
      _tabController = TabController(
        length: 1 + _playlists.length,
        vsync: this,
        initialIndex: oldIndex.clamp(0, _playlists.length),
      );
    });

    WidgetsBinding.instance.addPostFrameCallback((_) => oldController.dispose());
  }

  Future<void> _refreshAll() async {
    if (_connected) _requestServerState();
    await _podcastService.fetchEpisodes();
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
            ElevatedButton(onPressed: _downloadUpdate, child: const Text('Update'))
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
          StatusCard(
            device: _deviceStatus,
            progress: _syncProgress,
            onSyncNow: _connected ? _syncNow : null,
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                PodcastTab(
                  podcastService: _podcastService,
                  selection: _selection,
                  connected: _connected,
                  onRefresh: _refreshAll,
                  onSubmit: _submit,
                  lastRefreshed: _lastRefreshed,
                ),
                ..._playlists.map((p) => YouTubeTab(
                      key: ValueKey(p.id),
                      playlist: p,
                      mqttService: _mqttService,
                      connected: _connected,
                    )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
