import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';
import '../models/server_status.dart';

/// Connection state for the MQTT service
enum AppMqttConnectionState {
  disconnected,
  connecting,
  connected,
}

/// MQTT topics shared with the Pi (see api/src/open_swim/app.py).
class Topics {
  static const episodesToSync = 'openswim/episodes_to_sync';
  static const episodesToSyncRequest = 'openswim/episodes-to-sync/request';
  static const episodesToSyncResponse = 'openswim/episodes-to-sync/response';
  static const playlistsToSyncRequest = 'openswim/playlists-to-sync/request';
  static const playlistsToSyncResponse = 'openswim/playlists-to-sync/response';
  static const playlistInfoRequest = 'openswim/playlist-info/request';
  static const playlistInfoResponse = 'openswim/playlist-info/response';
  static const deviceStatus = 'openswim/device/status';
  static const syncProgress = 'openswim/sync/progress';
  static const syncRequest = 'openswim/sync/request';

  static const subscribed = [
    episodesToSyncResponse,
    playlistsToSyncResponse,
    playlistInfoResponse,
    deviceStatus,
    syncProgress,
  ];
}

class MqttService {
  MqttServerClient? client;
  final String broker = 'wss://mqtt.tenjo.ovh';
  final int port = 443;
  final String username = 'pi';
  final String password = 'hackol37';

  final _episodesToSync = StreamController<List<dynamic>>.broadcast();
  final _playlistsToSync = StreamController<List<dynamic>>.broadcast();
  final _playlistInfo = StreamController<PlaylistInfo>.broadcast();
  final _deviceStatus = StreamController<DeviceStatus>.broadcast();
  final _syncProgress = StreamController<SyncProgress>.broadcast();
  final _connectionState = StreamController<AppMqttConnectionState>.broadcast();

  Stream<List<dynamic>> get episodesToSyncResponse => _episodesToSync.stream;
  Stream<List<dynamic>> get playlistsToSyncResponse => _playlistsToSync.stream;
  Stream<PlaylistInfo> get playlistInfoResponse => _playlistInfo.stream;
  Stream<DeviceStatus> get deviceStatus => _deviceStatus.stream;
  Stream<SyncProgress> get syncProgress => _syncProgress.stream;
  Stream<AppMqttConnectionState> get connectionState => _connectionState.stream;

  AppMqttConnectionState _currentState = AppMqttConnectionState.disconnected;
  AppMqttConnectionState get currentConnectionState => _currentState;
  bool get isConnected =>
      client?.connectionStatus?.state == MqttConnectionState.connected;

  // Reconnection logic
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectDelay = 30;
  bool _intentionalDisconnect = false;
  StreamSubscription? _updatesSubscription;

  void _updateConnectionState(AppMqttConnectionState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _connectionState.add(newState);
      debugPrint('MQTT connection state: $newState');
    }
  }

  Future<bool> connect() async {
    if (_currentState == AppMqttConnectionState.connecting) {
      return false;
    }

    _intentionalDisconnect = false;
    _updateConnectionState(AppMqttConnectionState.connecting);

    await _updatesSubscription?.cancel();
    _updatesSubscription = null;

    final clientId = 'flutter_client_${DateTime.now().millisecondsSinceEpoch}';
    final c = MqttServerClient(broker, clientId);
    client = c;
    c.logging(on: false);
    // Short keep-alive plus no-response disconnect, so a dead socket (e.g.
    // after switching between Wi-Fi and mobile data) is noticed within
    // seconds instead of the app showing "Connected" indefinitely.
    c.keepAlivePeriod = 20;
    c.disconnectOnNoResponsePeriod = 10;
    // "Connected" is only announced after subscribing (below), so listeners
    // that send a request on connect never miss the reply.
    c.onDisconnected = _onDisconnected;
    c.useWebSocket = true;
    c.port = port;
    c.websocketProtocols = MqttClientConstants.protocolsSingleDefault;
    c.setProtocolV311();
    c.autoReconnect = false;
    c.connectionMessage = MqttConnectMessage()
        .withClientIdentifier(clientId)
        .authenticateAs(username, password)
        .startClean()
        .withWillQos(MqttQos.atMostOnce);

    try {
      debugPrint('Connecting to MQTT broker at $broker:$port...');
      await c.connect();
    } catch (e) {
      debugPrint('MQTT connection failed: $e');
      _updateConnectionState(AppMqttConnectionState.disconnected);
      _scheduleReconnect();
      return false;
    }

    if (!isConnected) {
      debugPrint('MQTT connection failed - status: ${c.connectionStatus}');
      _updateConnectionState(AppMqttConnectionState.disconnected);
      _scheduleReconnect();
      return false;
    }

    _reconnectAttempts = 0;
    _updatesSubscription = c.updates!.listen(_onMessages);
    for (final topic in Topics.subscribed) {
      c.subscribe(topic, MqttQos.atLeastOnce);
    }
    _updateConnectionState(AppMqttConnectionState.connected);
    return true;
  }

  void _scheduleReconnect() {
    if (_intentionalDisconnect) return;

    _reconnectTimer?.cancel();

    // Exponential backoff: 1, 2, 4, 8, 16, 30, 30...
    final delay = (1 << _reconnectAttempts.clamp(0, 5)).clamp(1, _maxReconnectDelay);
    _reconnectAttempts++;

    debugPrint('MQTT reconnect attempt $_reconnectAttempts in ${delay}s');
    _reconnectTimer = Timer(Duration(seconds: delay), connect);
  }

  /// Manual reconnect - resets the backoff.
  Future<bool> reconnect() async {
    _reconnectTimer?.cancel();
    _reconnectAttempts = 0;
    return await connect();
  }

  void _onMessages(List<MqttReceivedMessage<MqttMessage>> messages) {
    // A batch can hold several messages (e.g. retained ones on subscribe).
    for (final received in messages) {
      final message = received.payload as MqttPublishMessage;
      final payload = MqttPublishPayload.bytesToStringAsString(message.payload.message);
      _route(received.topic, payload);
    }
  }

  void _route(String topic, String payload) {
    switch (topic) {
      case Topics.episodesToSyncResponse:
        final list = _parseList(payload);
        if (list != null) _episodesToSync.add(list);
      case Topics.playlistsToSyncResponse:
        final list = _parseList(payload);
        if (list != null) _playlistsToSync.add(list);
      case Topics.playlistInfoResponse:
        final info = PlaylistInfo.parse(payload);
        if (info != null) _playlistInfo.add(info);
      case Topics.deviceStatus:
        _deviceStatus.add(DeviceStatus.parse(payload));
      case Topics.syncProgress:
        final progress = SyncProgress.parse(payload);
        if (progress != null) _syncProgress.add(progress);
      default:
        debugPrint('Unhandled MQTT topic $topic');
    }
  }

  List<dynamic>? _parseList(String payload) {
    if (payload.isEmpty) return [];
    try {
      return json.decode(payload) as List<dynamic>;
    } catch (e) {
      debugPrint('Bad JSON list payload: $e');
      return null;
    }
  }

  /// Publish a message. Returns false when not connected; nothing is queued,
  /// because the Pi does not keep messages sent while it is away.
  bool publishMessage(String topic, String message) {
    if (!isConnected) {
      debugPrint('Cannot publish to $topic - not connected');
      return false;
    }
    final builder = MqttClientPayloadBuilder()..addString(message);
    client!.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
    return true;
  }

  void requestEpisodesToSync() => publishMessage(Topics.episodesToSyncRequest, '');

  void requestPlaylistsToSync() => publishMessage(Topics.playlistsToSyncRequest, '');

  /// Ask the Pi to sync now (e.g. after adding videos to a playlist on YouTube).
  bool requestSync() => publishMessage(Topics.syncRequest, '');

  bool requestPlaylistInfo(String playlistId) => publishMessage(
        Topics.playlistInfoRequest,
        json.encode({'playlist_id': playlistId}),
      );

  void _onDisconnected() {
    _updateConnectionState(AppMqttConnectionState.disconnected);
    if (!_intentionalDisconnect) {
      _scheduleReconnect();
    }
  }

  void dispose() {
    _intentionalDisconnect = true;
    _reconnectTimer?.cancel();
    _updatesSubscription?.cancel();
    client?.disconnect();
    _episodesToSync.close();
    _playlistsToSync.close();
    _playlistInfo.close();
    _deviceStatus.close();
    _syncProgress.close();
    _connectionState.close();
  }
}
