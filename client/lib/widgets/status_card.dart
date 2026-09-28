import 'package:flutter/material.dart';
import '../models/server_status.dart';

String formatWhen(DateTime at, {DateTime? now}) {
  final current = now ?? DateTime.now();
  final hhmm =
      '${at.hour.toString().padLeft(2, '0')}:${at.minute.toString().padLeft(2, '0')}';
  final today = DateTime(current.year, current.month, current.day);
  final day = DateTime(at.year, at.month, at.day);
  final days = today.difference(day).inDays;
  if (days == 0) return 'today $hhmm';
  if (days == 1) return 'yesterday $hhmm';
  return '${at.day}/${at.month} $hhmm';
}

/// The player's state and the outcome of the current or last sync.
class StatusCard extends StatelessWidget {
  final DeviceStatus device;
  final SyncProgress? progress;

  const StatusCard({super.key, required this.device, this.progress});

  (IconData, Color, String) _player() {
    switch (device.state) {
      case PlayerState.safeToUnplug:
        final when = device.at != null ? ' (${formatWhen(device.at!)})' : '';
        return (Icons.check_circle, Colors.green.shade700, 'Player synced, safe to unplug$when');
      case PlayerState.connected:
        return (Icons.usb, Colors.orange.shade800, 'Player plugged in, don\'t unplug yet');
      case PlayerState.disconnected:
        return (Icons.usb_off, Colors.grey.shade700, 'Player not plugged in');
      case PlayerState.unknown:
        return (Icons.help_outline, Colors.grey.shade600, 'Player status unknown');
    }
  }

  (IconData, Color, String) _sync() {
    final p = progress;
    if (p == null || p.stages.isEmpty) {
      return (Icons.sync_disabled, Colors.grey.shade600, 'No sync reported yet');
    }
    if (p.isRunning) {
      return (Icons.sync, Colors.blue.shade700, 'Syncing: ${p.current?.label ?? ''}…');
    }
    final when = p.at != null ? ' ${formatWhen(p.at!)}' : '';
    if (p.hasErrors) {
      final failed = p.stages.where((s) => s.state == StageState.error).length;
      return (Icons.error_outline, Colors.red.shade700,
          'Last sync$when: $failed step${failed == 1 ? '' : 's'} failed (tap for details)');
    }
    return (Icons.done_all, Colors.green.shade700, 'Last sync$when finished');
  }

  void _showDetails(BuildContext context) {
    final p = progress;
    if (p == null) return;
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Last sync'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final stage in p.stages)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Text(
                    '${switch (stage.state) {
                      StageState.completed => '✓',
                      StageState.error => '✗',
                      StageState.running => '…',
                      StageState.pending => '·',
                    }} ${stage.label}${stage.error != null ? '\n   ${stage.error}' : ''}',
                  ),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final (playerIcon, playerColor, playerText) = _player();
    final (syncIcon, syncColor, syncText) = _sync();
    return Material(
      color: Colors.grey.shade100,
      child: InkWell(
        onTap: progress == null ? null : () => _showDetails(context),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _line(playerIcon, playerColor, playerText),
              const SizedBox(height: 4),
              _line(syncIcon, syncColor, syncText),
            ],
          ),
        ),
      ),
    );
  }

  Widget _line(IconData icon, Color color, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: TextStyle(fontSize: 13, color: color))),
      ],
    );
  }
}
