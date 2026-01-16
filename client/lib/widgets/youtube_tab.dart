import 'package:flutter/material.dart';

class YouTubePlaylist {
  final String id;
  final String title;

  const YouTubePlaylist({required this.id, required this.title});
}

class YouTubeTab extends StatelessWidget {
  final YouTubePlaylist playlist;

  const YouTubeTab({
    super.key,
    required this.playlist,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.play_circle_outline,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            playlist.title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.grey.shade700,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'YouTube playlist content coming soon',
            style: TextStyle(
              color: Colors.grey.shade500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'ID: ${playlist.id}',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade400,
            ),
          ),
        ],
      ),
    );
  }
}
