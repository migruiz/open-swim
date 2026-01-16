import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';

class EpisodeTile extends StatelessWidget {
  final PodcastEpisode episode;
  final bool isSyncedOnly;
  final ValueChanged<bool?> onChanged;

  const EpisodeTile({
    super.key,
    required this.episode,
    required this.onChanged,
    this.isSyncedOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    return CheckboxListTile(
      value: episode.isSelected,
      onChanged: onChanged,
      title: Row(
        children: [
          Expanded(
            child: Text(
              episode.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 14),
            ),
          ),
          if (isSyncedOnly)
            Container(
              margin: const EdgeInsets.only(left: 8),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.blue.shade100,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Synced',
                style: TextStyle(
                  fontSize: 10,
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
        ],
      ),
      subtitle: Row(
        children: [
          Text(
            episode.formattedDate,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
            ),
          ),
          if (episode.durationSeconds > 0) ...[
            const SizedBox(width: 8),
            Icon(Icons.timer_outlined, size: 12, color: Colors.grey.shade600),
            const SizedBox(width: 2),
            Text(
              episode.formattedDuration,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ],
      ),
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: const EdgeInsets.symmetric(horizontal: 8),
      dense: true,
    );
  }
}
