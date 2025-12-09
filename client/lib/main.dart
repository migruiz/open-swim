import 'dart:async';
import 'package:flutter/material.dart';
import 'services/mqtt_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Open Swim',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MyHomePage(title: 'Open Swim'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _counter = 0;
  final MqttService _mqttService = MqttService();
  AppMqttConnectionState _connectionState = AppMqttConnectionState.disconnected;
  final List<String> _messages = [];

  StreamSubscription<AppMqttConnectionState>? _connectionStateSubscription;
  StreamSubscription<String>? _messagesSubscription;

  @override
  void initState() {
    super.initState();

    // Listen to connection state changes
    _connectionStateSubscription =
        _mqttService.connectionState.listen((state) {
      setState(() {
        _connectionState = state;
      });
    });

    // Listen to messages
    _messagesSubscription = _mqttService.messages.listen((message) {
      setState(() {
        _messages.add(message);
      });
    });

    // Initial connection
    _mqttService.connect();
  }

  @override
  void dispose() {
    _connectionStateSubscription?.cancel();
    _messagesSubscription?.cancel();
    _mqttService.dispose();
    super.dispose();
  }

  void _incrementCounter() {
    setState(() {
      _counter++;
    });
    if (_connectionState == AppMqttConnectionState.connected) {
      _mqttService.publishMessage(
          'openswim/device/status', 'Counter: $_counter');
    }
  }

  Color _getConnectionColor() {
    switch (_connectionState) {
      case AppMqttConnectionState.connected:
        return Colors.green.shade700;
      case AppMqttConnectionState.connecting:
        return Colors.orange.shade700;
      case AppMqttConnectionState.disconnected:
        return Colors.red.shade700;
    }
  }

  String _getConnectionText() {
    switch (_connectionState) {
      case AppMqttConnectionState.connected:
        return 'Connected to MQTT';
      case AppMqttConnectionState.connecting:
        return 'Connecting...';
      case AppMqttConnectionState.disconnected:
        return 'Disconnected - Tap to retry';
    }
  }

  Widget _buildConnectionIcon() {
    switch (_connectionState) {
      case AppMqttConnectionState.connected:
        return Icon(Icons.check_circle, color: _getConnectionColor(), size: 20);
      case AppMqttConnectionState.connecting:
        return SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(_getConnectionColor()),
          ),
        );
      case AppMqttConnectionState.disconnected:
        return Icon(Icons.error, color: _getConnectionColor(), size: 20);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Connection status with manual reconnect
            GestureDetector(
              onTap: _connectionState == AppMqttConnectionState.disconnected
                  ? () => _mqttService.reconnect()
                  : null,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _getConnectionColor().withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: _getConnectionColor()),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildConnectionIcon(),
                    const SizedBox(width: 8),
                    Text(
                      _getConnectionText(),
                      style: TextStyle(
                        color: _getConnectionColor(),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (_connectionState ==
                        AppMqttConnectionState.disconnected) ...[
                      const SizedBox(width: 8),
                      Icon(
                        Icons.refresh,
                        size: 18,
                        color: _getConnectionColor(),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            const Text('You have pushed the button this many times:'),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 32),
            // Messages section
            if (_messages.isNotEmpty) ...[
              const Text(
                'Received Messages:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: ListView.builder(
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      return ListTile(
                        dense: true,
                        title: Text(_messages[index]),
                      );
                    },
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment & Publish',
        child: const Icon(Icons.add),
      ),
    );
  }
}
