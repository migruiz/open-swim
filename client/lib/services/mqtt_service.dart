import 'dart:async';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

/// Connection state for the MQTT service
enum AppMqttConnectionState {
  disconnected,
  connecting,
  connected,
}

class MqttService {
  MqttServerClient? client;
  final String broker = 'wss://mqtt.tenjo.ovh';
  final int port = 443;
  final String username = 'pi';
  final String password = 'hackol37';

  // Message stream
  final StreamController<String> _messageController =
      StreamController<String>.broadcast();
  Stream<String> get messages => _messageController.stream;

  // Connection state stream
  final StreamController<AppMqttConnectionState> _connectionStateController =
      StreamController<AppMqttConnectionState>.broadcast();
  Stream<AppMqttConnectionState> get connectionState =>
      _connectionStateController.stream;
  AppMqttConnectionState _currentState = AppMqttConnectionState.disconnected;
  AppMqttConnectionState get currentConnectionState => _currentState;

  // Reconnection logic
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectDelay = 30;
  static const int _baseReconnectDelay = 1;
  bool _intentionalDisconnect = false;

  // Topic tracking for re-subscription
  final Set<String> _subscribedTopics = {};
  StreamSubscription? _updatesSubscription;

  void _updateConnectionState(AppMqttConnectionState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _connectionStateController.add(newState);
      print('Connection state changed to: $newState');
    }
  }

  Future<bool> connect() async {
    // Prevent multiple simultaneous connection attempts
    if (_currentState == AppMqttConnectionState.connecting) {
      return false;
    }

    _intentionalDisconnect = false;
    _updateConnectionState(AppMqttConnectionState.connecting);

    // Cancel any existing updates subscription
    await _updatesSubscription?.cancel();
    _updatesSubscription = null;

    // Create new client with fresh clientId for each connection
    final newClientId = 'flutter_client_${DateTime.now().millisecondsSinceEpoch}';
    client = MqttServerClient(broker, newClientId);
    client!.logging(on: true);
    client!.keepAlivePeriod = 60;
    client!.onConnected = _onConnected;
    client!.onDisconnected = _onDisconnected;
    client!.onSubscribed = _onSubscribed;
    client!.pongCallback = _onPong;
    client!.useWebSocket = true;
    client!.port = port;
    client!.websocketProtocols = MqttClientConstants.protocolsSingleDefault;
    client!.setProtocolV311();
    client!.autoReconnect = false;

    final connMessage = MqttConnectMessage()
        .withClientIdentifier(newClientId)
        .authenticateAs(username, password)
        .startClean()
        .withWillQos(MqttQos.atMostOnce);

    client!.connectionMessage = connMessage;

    try {
      print('Connecting to MQTT broker at $broker:$port...');
      await client!.connect();
    } catch (e) {
      print('Connection failed: $e');
      _updateConnectionState(AppMqttConnectionState.disconnected);
      _scheduleReconnect();
      return false;
    }

    if (client!.connectionStatus!.state == MqttConnectionState.connected) {
      print('Connected to MQTT broker successfully');
      _reconnectAttempts = 0;
      _updateConnectionState(AppMqttConnectionState.connected);

      // Re-subscribe to all tracked topics
      _resubscribeToTopics();

      return true;
    } else {
      print('Connection failed - status: ${client!.connectionStatus}');
      _updateConnectionState(AppMqttConnectionState.disconnected);
      _scheduleReconnect();
      return false;
    }
  }

  void _scheduleReconnect() {
    if (_intentionalDisconnect) {
      print('Intentional disconnect - not scheduling reconnect');
      return;
    }

    _reconnectTimer?.cancel();

    // Exponential backoff: 1, 2, 4, 8, 16, 30, 30...
    final delay = (_baseReconnectDelay * (1 << _reconnectAttempts))
        .clamp(1, _maxReconnectDelay);
    _reconnectAttempts++;

    print('Scheduling reconnect attempt $_reconnectAttempts in $delay seconds...');

    _reconnectTimer = Timer(Duration(seconds: delay), () {
      print('Attempting reconnect (attempt $_reconnectAttempts)...');
      connect();
    });
  }

  /// Manual reconnect - resets attempt counter
  Future<bool> reconnect() async {
    print('Manual reconnect requested');
    _reconnectTimer?.cancel();
    _reconnectAttempts = 0;
    return await connect();
  }

  void subscribeToTopic(String topic) {
    // Always track the topic for re-subscription
    _subscribedTopics.add(topic);

    if (client?.connectionStatus?.state != MqttConnectionState.connected) {
      print('Cannot subscribe to $topic - not connected (will subscribe when connected)');
      return;
    }

    print('Subscribing to topic: $topic');
    client!.subscribe(topic, MqttQos.atLeastOnce);

    // Set up updates listener if not already set
    if (_updatesSubscription == null) {
      _setupUpdatesListener();
    }
  }

  void _setupUpdatesListener() {
    _updatesSubscription?.cancel();
    _updatesSubscription = client!.updates!
        .listen((List<MqttReceivedMessage<MqttMessage>> messages) {
      final recMess = messages[0].payload as MqttPublishMessage;
      final payload =
          MqttPublishPayload.bytesToStringAsString(recMess.payload.message);

      print('Received message on topic ${messages[0].topic}: $payload');
      _messageController.add(payload);
    });
  }

  void _resubscribeToTopics() {
    if (_subscribedTopics.isEmpty) {
      // Default topic if no topics tracked
      subscribeToTopic('openswim/device/status');
    } else {
      // Set up listener first
      _setupUpdatesListener();

      // Then subscribe to all tracked topics
      for (final topic in _subscribedTopics) {
        print('Re-subscribing to topic: $topic');
        client!.subscribe(topic, MqttQos.atLeastOnce);
      }
    }
  }

  void publishMessage(String topic, String message) {
    if (client?.connectionStatus?.state == MqttConnectionState.connected) {
      final builder = MqttClientPayloadBuilder();
      builder.addString(message);

      print('Publishing message to $topic: $message');
      client!.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
    } else {
      print('Cannot publish - not connected');
    }
  }

  void disconnect() {
    _intentionalDisconnect = true;
    _reconnectTimer?.cancel();
    client?.disconnect();
  }

  void _onConnected() {
    print('MQTT Client connected');
    _updateConnectionState(AppMqttConnectionState.connected);
  }

  void _onDisconnected() {
    print('MQTT Client disconnected');
    _updateConnectionState(AppMqttConnectionState.disconnected);

    if (!_intentionalDisconnect) {
      _scheduleReconnect();
    }
  }

  void _onSubscribed(String topic) {
    print('Subscribed to topic: $topic');
  }

  void _onPong() {
    print('Ping response received');
  }

  void dispose() {
    _intentionalDisconnect = true;
    _reconnectTimer?.cancel();
    _updatesSubscription?.cancel();
    _messageController.close();
    _connectionStateController.close();
    client?.disconnect();
  }
}
