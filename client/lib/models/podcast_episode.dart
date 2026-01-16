class PodcastEpisode {
  final String id;
  final String title;
  final DateTime published;
  final int durationSeconds;
  final String mediaUrl;
  bool isSelected;

  PodcastEpisode({
    required this.id,
    required this.title,
    required this.published,
    required this.durationSeconds,
    required this.mediaUrl,
    this.isSelected = false,
  });

  /// Parse from podbay.fm API response
  factory PodcastEpisode.fromJson(Map<String, dynamic> json) {
    final durationStr = json['duration'] as String? ?? '0';
    return PodcastEpisode(
      id: json['_id'] as String,
      title: json['title'] as String,
      published: DateTime.parse(json['published'] as String),
      durationSeconds: int.tryParse(durationStr) ?? 0,
      mediaUrl: json['mediaURL'] as String,
    );
  }

  /// Parse from API sync response
  factory PodcastEpisode.fromSyncJson(Map<String, dynamic> json) {
    return PodcastEpisode(
      id: json['id'] as String,
      title: json['title'] as String,
      published: DateTime.parse(json['date'] as String),
      durationSeconds: 0,
      mediaUrl: json['download_url'] as String,
      isSelected: true,
    );
  }

  /// Convert to sync JSON payload for MQTT
  Map<String, dynamic> toSyncJson() {
    return {
      'id': id,
      'date': published.toIso8601String(),
      'title': title,
      'download_url': mediaUrl,
    };
  }

  /// Convert to JSON for caching (matches fromJson format)
  Map<String, dynamic> toJson() {
    return {
      '_id': id,
      'title': title,
      'published': published.toIso8601String(),
      'duration': durationSeconds.toString(),
      'mediaURL': mediaUrl,
    };
  }

  String get formattedDuration {
    final hours = durationSeconds ~/ 3600;
    final minutes = (durationSeconds % 3600) ~/ 60;
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    }
    return '${minutes}m';
  }

  String get formattedDate {
    final now = DateTime.now();
    final diff = now.difference(published);
    if (diff.inDays == 0) {
      return 'Today';
    } else if (diff.inDays == 1) {
      return 'Yesterday';
    } else if (diff.inDays < 7) {
      return '${diff.inDays} days ago';
    } else {
      return '${published.month}/${published.day}/${published.year}';
    }
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PodcastEpisode &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;
}
