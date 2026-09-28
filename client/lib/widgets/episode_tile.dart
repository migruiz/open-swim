import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';

class EpisodeTile extends StatelessWidget {
  final PodcastEpisode episode;
  final bool selected;

  /// False until the Pi's picks have arrived; see [SelectionController.loaded].
  final bool enabled;
  final VoidCallback onToggle;

  const EpisodeTile({
    super.key,
    required this.episode,
    required this.selected,
    required this.enabled,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final grey = Colors.grey.shade600;
    return CheckboxListTile(
      value: selected,
      onChanged: enabled ? (_) => onToggle() : null,
      title: Text(
        episode.title,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 14),
      ),
      subtitle: Row(
        children: [
          Text(episode.formattedDate, style: TextStyle(fontSize: 12, color: grey)),
          if (episode.durationSeconds > 0) ...[
            const SizedBox(width: 8),
            Icon(Icons.timer_outlined, size: 12, color: grey),
            const SizedBox(width: 2),
            Text(episode.formattedDuration, style: TextStyle(fontSize: 12, color: grey)),
          ],
        ],
      ),
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: const EdgeInsets.symmetric(horizontal: 8),
      dense: true,
    );
  }
}
