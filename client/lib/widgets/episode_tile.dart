import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';

class EpisodeTile extends StatelessWidget {
  final PodcastEpisode episode;
  final bool selected;

  /// False until the Pi's picks have arrived; see [SelectionController.loaded].
  final bool enabled;
  final VoidCallback onToggle;

  /// The part to start from. The part row shows only when [onStartPartChanged]
  /// is set, which the podcast tab does for picked episodes.
  final int startPart;

  /// Null until the Pi has split the episode into parts.
  final int? partCount;
  final ValueChanged<int>? onStartPartChanged;

  const EpisodeTile({
    super.key,
    required this.episode,
    required this.selected,
    required this.enabled,
    required this.onToggle,
    this.startPart = 1,
    this.partCount,
    this.onStartPartChanged,
  });

  @override
  Widget build(BuildContext context) {
    final grey = Colors.grey.shade600;
    final details = Row(
      children: [
        Text(episode.formattedDate, style: TextStyle(fontSize: 12, color: grey)),
        if (episode.durationSeconds > 0) ...[
          const SizedBox(width: 8),
          Icon(Icons.timer_outlined, size: 12, color: grey),
          const SizedBox(width: 2),
          Text(episode.formattedDuration, style: TextStyle(fontSize: 12, color: grey)),
        ],
      ],
    );
    return CheckboxListTile(
      value: selected,
      onChanged: enabled ? (_) => onToggle() : null,
      title: Text(
        episode.title,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 14),
      ),
      subtitle: onStartPartChanged == null
          ? details
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [details, _partRow(grey)],
            ),
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: const EdgeInsets.symmetric(horizontal: 8),
      dense: true,
    );
  }

  Widget _partRow(Color grey) {
    final change = onStartPartChanged!;
    final count = partCount;
    final label = count == null ? 'Start at part $startPart' : 'Start at part $startPart of $count';
    Widget button(IconData icon, String tooltip, int? to) => IconButton(
          icon: Icon(icon, size: 18),
          tooltip: tooltip,
          visualDensity: VisualDensity.compact,
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 36, minHeight: 32),
          onPressed: enabled && to != null ? () => change(to) : null,
        );
    return Row(
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: grey)),
        const Spacer(),
        button(Icons.remove, 'Earlier part', startPart > 1 ? startPart - 1 : null),
        button(Icons.add, 'Later part', count == null || startPart < count ? startPart + 1 : null),
      ],
    );
  }
}
