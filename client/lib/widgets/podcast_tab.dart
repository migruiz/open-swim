import 'dart:async';
import 'package:flutter/material.dart';
import '../models/podcast_episode.dart';
import '../services/podcast_service.dart';
import '../state/selection_controller.dart';
import 'episode_tile.dart';

class PodcastTab extends StatefulWidget {
  final PodcastService podcastService;
  final SelectionController selection;
  final bool connected;
  final VoidCallback onRefresh;
  final VoidCallback onSubmit;
  final DateTime? lastRefreshed;

  const PodcastTab({
    super.key,
    required this.podcastService,
    required this.selection,
    required this.connected,
    required this.onRefresh,
    required this.onSubmit,
    this.lastRefreshed,
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
      if (mounted) setState(() => _episodes = episodes);
    });
    _loadingSubscription = widget.podcastService.isLoading.listen((isLoading) {
      if (mounted) setState(() => _isLoading = isLoading);
    });
    _errorSubscription = widget.podcastService.error.listen((error) {
      if (mounted) setState(() => _error = error);
    });

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

  String _formatLastRefreshed(DateTime? timestamp) {
    if (timestamp == null) return 'Never';

    final diff = DateTime.now().difference(timestamp);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) {
      return '${diff.inMinutes} ${diff.inMinutes == 1 ? 'minute' : 'minutes'} ago';
    }
    if (diff.inHours < 24) {
      return '${diff.inHours} ${diff.inHours == 1 ? 'hour' : 'hours'} ago';
    }
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays} days ago';
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${months[timestamp.month - 1]} ${timestamp.day}';
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Text(
            'Feed refreshed: ${_formatLastRefreshed(widget.lastRefreshed)}',
            style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: widget.onRefresh,
            tooltip: 'Refresh',
          ),
        ],
      ),
    );
  }

  Widget _buildWaitingBanner() {
    final text = widget.connected
        ? 'Loading your picks from the Pi… You can change picks once they arrive.'
        : 'Not connected. Picks can only be changed while connected to the Pi.';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Colors.amber.shade100,
      child: Text(text, style: const TextStyle(fontSize: 13)),
    );
  }

  Widget _sectionHeader(String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Colors.grey.shade700,
        ),
      ),
    );
  }

  Widget _buildSubmitBar() {
    final selection = widget.selection;
    final count = selection.changeCount;
    final sending = selection.awaitingConfirmation;
    return Material(
      elevation: 8,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  !widget.connected
                      ? '$count unsent change${count == 1 ? '' : 's'} (not connected)'
                      : '$count unsent change${count == 1 ? '' : 's'}',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
              ),
              TextButton(
                onPressed: sending ? null : selection.discardChanges,
                child: const Text('Discard'),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: widget.connected && !sending ? widget.onSubmit : null,
                icon: sending
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send, size: 18),
                label: Text(sending ? 'Sending' : 'Submit'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.selection,
      builder: (context, _) {
        final selection = widget.selection;
        final picked = selection.selectedEpisodes(_episodes);

        Widget tile(PodcastEpisode episode) => EpisodeTile(
              episode: episode,
              selected: selection.isSelected(episode.id),
              enabled: selection.loaded && !selection.awaitingConfirmation,
              onToggle: () => selection.toggle(episode.id),
            );

        final Widget body;
        if (_isLoading && _episodes.isEmpty && picked.isEmpty) {
          body = const Center(child: CircularProgressIndicator());
        } else {
          // Row builders, so the ~1,600-episode feed is built lazily.
          final rows = <Widget Function()>[
            if (_error != null && _episodes.isEmpty)
              () => ListTile(
                    leading: Icon(Icons.error_outline, color: Colors.red.shade300),
                    title: const Text('Failed to load the podcast feed'),
                    trailing: TextButton(
                      onPressed: widget.onRefresh,
                      child: const Text('Retry'),
                    ),
                  ),
            () => _sectionHeader('PICKED FOR THE PLAYER (${picked.length})'),
            if (picked.isEmpty)
              () => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Text(
                      'Nothing picked. Tick episodes below, then Submit.',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ),
            for (final episode in picked) () => tile(episode),
            () => const Divider(),
            () => _sectionHeader('ALL EPISODES'),
            for (final episode in _episodes) () => tile(episode),
          ];
          body = ListView.builder(
            itemCount: rows.length,
            itemBuilder: (context, index) => rows[index](),
          );
        }

        return Column(
          children: [
            _buildHeader(),
            if (!selection.loaded) _buildWaitingBanner(),
            Expanded(child: body),
            if (selection.hasChanges || selection.awaitingConfirmation) _buildSubmitBar(),
          ],
        );
      },
    );
  }
}
