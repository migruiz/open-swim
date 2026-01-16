import 'dart:async';
import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';
import '../services/podcast_service.dart';
import 'episode_tile.dart';

class PodcastTab extends StatefulWidget {
  final PodcastService podcastService;
  final Set<String> syncedEpisodeIds;
  final ValueChanged<PodcastEpisode> onEpisodeToggled;

  const PodcastTab({
    super.key,
    required this.podcastService,
    required this.syncedEpisodeIds,
    required this.onEpisodeToggled,
  });

  @override
  State<PodcastTab> createState() => _PodcastTabState();
}

class _PodcastTabState extends State<PodcastTab> {
  List<PodcastEpisode> _episodes = [];
  bool _isLoading = true;
  String? _error;

  StreamSubscription<List<PodcastEpisode>>? _episodesSubscription;
  StreamSubscription<bool>? _loadingSubscription;
  StreamSubscription<String?>? _errorSubscription;

  @override
  void initState() {
    super.initState();

    _episodesSubscription = widget.podcastService.episodes.listen((episodes) {
      if (mounted) {
        setState(() {
          _episodes = episodes;
        });
      }
    });

    _loadingSubscription = widget.podcastService.isLoading.listen((isLoading) {
      if (mounted) {
        setState(() {
          _isLoading = isLoading;
        });
      }
    });

    _errorSubscription = widget.podcastService.error.listen((error) {
      if (mounted) {
        setState(() {
          _error = error;
        });
      }
    });

    // Fetch episodes if not already loaded
    if (widget.podcastService.cachedEpisodes.isEmpty) {
      widget.podcastService.fetchEpisodes();
    } else {
      _episodes = widget.podcastService.cachedEpisodes;
      _isLoading = false;
    }
  }

  @override
  void dispose() {
    _episodesSubscription?.cancel();
    _loadingSubscription?.cancel();
    _errorSubscription?.cancel();
    super.dispose();
  }

  List<_EpisodeListItem> _buildEpisodeList() {
    final items = <_EpisodeListItem>[];

    // First, add synced episodes that are NOT in the podcast list (synced-only)
    final podcastIds = _episodes.map((e) => e.id).toSet();
    for (final syncedId in widget.syncedEpisodeIds) {
      if (!podcastIds.contains(syncedId)) {
        // Create a placeholder episode for synced-only items
        items.add(_EpisodeListItem(
          episode: PodcastEpisode(
            id: syncedId,
            title: 'Episode (synced)',
            published: DateTime.now(),
            durationSeconds: 0,
            mediaUrl: '',
            isSelected: true,
          ),
          isSyncedOnly: true,
        ));
      }
    }

    // Then add all podcast episodes
    for (final episode in _episodes) {
      items.add(_EpisodeListItem(
        episode: episode,
        isSyncedOnly: false,
      ));
    }

    return items;
  }

  Future<void> _refresh() async {
    await widget.podcastService.fetchEpisodes();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading && _episodes.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null && _episodes.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text(
              'Failed to load episodes',
              style: TextStyle(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _refresh,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final items = _buildEpisodeList();

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.separated(
        itemCount: items.length,
        separatorBuilder: (context, index) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final item = items[index];
          return EpisodeTile(
            episode: item.episode,
            isSyncedOnly: item.isSyncedOnly,
            onChanged: (value) {
              widget.onEpisodeToggled(item.episode);
            },
          );
        },
      ),
    );
  }
}

class _EpisodeListItem {
  final PodcastEpisode episode;
  final bool isSyncedOnly;

  _EpisodeListItem({
    required this.episode,
    required this.isSyncedOnly,
  });
}
