import 'package:flutter/material.dart';
import '../services/mqtt_service.dart';

class ConnectionStatusBar extends StatelessWidget {
  final AppMqttConnectionState connectionState;
  final VoidCallback? onReconnect;

  const ConnectionStatusBar({
    super.key,
    required this.connectionState,
    this.onReconnect,
  });

  Color _getConnectionColor() {
    switch (connectionState) {
      case AppMqttConnectionState.connected:
        return Colors.green.shade700;
      case AppMqttConnectionState.connecting:
        return Colors.orange.shade700;
      case AppMqttConnectionState.disconnected:
        return Colors.red.shade700;
    }
  }

  String _getConnectionText() {
    switch (connectionState) {
      case AppMqttConnectionState.connected:
        return 'Connected';
      case AppMqttConnectionState.connecting:
        return 'Connecting...';
      case AppMqttConnectionState.disconnected:
        return 'Disconnected';
    }
  }

  Widget _buildConnectionIcon() {
    final color = _getConnectionColor();
    switch (connectionState) {
      case AppMqttConnectionState.connected:
        return Icon(Icons.check_circle, color: color, size: 16);
      case AppMqttConnectionState.connecting:
        return SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        );
      case AppMqttConnectionState.disconnected:
        return Icon(Icons.error, color: color, size: 16);
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: connectionState == AppMqttConnectionState.disconnected
          ? onReconnect
          : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: _getConnectionColor().withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _getConnectionColor()),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildConnectionIcon(),
            const SizedBox(width: 6),
            Text(
              _getConnectionText(),
              style: TextStyle(
                color: _getConnectionColor(),
                fontWeight: FontWeight.w500,
                fontSize: 12,
              ),
            ),
            if (connectionState == AppMqttConnectionState.disconnected) ...[
              const SizedBox(width: 4),
              Icon(
                Icons.refresh,
                size: 14,
                color: _getConnectionColor(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
