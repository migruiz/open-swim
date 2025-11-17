import 'dart:async';
import 'dart:io';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

class MqttService {
  MqttServerClient? client;
  final String broker = 'mqtt.piscos.ovh';
  final int port = 443;
  final String clientId = 'flutter_client_${DateTime.now().millisecondsSinceEpoch}';
  
  final StreamController<String> _messageController = StreamController<String>.broadcast();
  Stream<String> get messages => _messageController.stream;

  Future<bool> connect() async {
    client = MqttServerClient.withPort(broker, clientId, port);
    client!.logging(on: true);
    client!.keepAlivePeriod = 60;
    client!.onConnected = onConnected;
    client!.onDisconnected = onDisconnected;
    client!.onSubscribed = onSubscribed;
    client!.pongCallback = pong;
    client!.secure = true;
    client!.securityContext = SecurityContext.defaultContext;
    client!.websocketProtocols = MqttClientConstants.protocolsSingleDefault;

    final connMessage = MqttConnectMessage()
        .withClientIdentifier(clientId)
        .startClean()
        .withWillQos(MqttQos.atLeastOnce);
    
    client!.connectionMessage = connMessage;

    try {
      print('Connecting to MQTT broker at wss://$broker:$port...');
      await client!.connect();
    } catch (e) {
      print('Connection failed: $e');
      client!.disconnect();
      return false;
    }

    if (client!.connectionStatus!.state == MqttConnectionState.connected) {
      print('Connected to MQTT broker successfully');
      
      // Subscribe to topic
      subscribeToTopic('openswim/device/status');
      
      // Publish a message
      publishMessage('openswim/device/status', 'Hello from Flutter client!');
      
      return true;
    } else {
      print('Connection failed - status: ${client!.connectionStatus}');
      client!.disconnect();
      return false;
    }
  }

  void subscribeToTopic(String topic) {
    if (client?.connectionStatus?.state == MqttConnectionState.connected) {
      print('Subscribing to topic: $topic');
      client!.subscribe(topic, MqttQos.atLeastOnce);
      
      client!.updates!.listen((List<MqttReceivedMessage<MqttMessage>> messages) {
        final recMess = messages[0].payload as MqttPublishMessage;
        final payload = MqttPublishPayload.bytesToStringAsString(recMess.payload.message);
        
        print('Received message on topic ${messages[0].topic}: $payload');
        _messageController.add(payload);
      });
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
    client?.disconnect();
  }

  void onConnected() {
    print('MQTT Client connected');
  }

  void onDisconnected() {
    print('MQTT Client disconnected');
  }

  void onSubscribed(String topic) {
    print('Subscribed to topic: $topic');
  }

  void pong() {
    print('Ping response received');
  }

  void dispose() {
    _messageController.close();
    disconnect();
  }
}
