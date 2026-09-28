import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:xml/xml.dart';
import '../models/podcast_episode.dart';

class PodcastService {
  static const String _feedUrl =
      'https://rss-cmg.streamguys1.com/sanantonio/san995/the-billy-madison-sh.xml';
  static const String _cacheKeyEpisodes = 'podcast_episodes';
  static const String _cacheKeyLastRefreshed = 'podcast_last_refreshed';

  final StreamController<List<PodcastEpisode>> _episodesController =
      StreamController<List<PodcastEpisode>>.broadcast();
  Stream<List<PodcastEpisode>> get episodes => _episodesController.stream;

  final StreamController<bool> _loadingController =
      StreamController<bool>.broadcast();
  Stream<bool> get isLoading => _loadingController.stream;

  final StreamController<String?> _errorController =
      StreamController<String?>.broadcast();
  Stream<String?> get error => _errorController.stream;

  final StreamController<DateTime?> _lastRefreshedController =
      StreamController<DateTime?>.broadcast();
  Stream<DateTime?> get lastRefreshedStream => _lastRefreshedController.stream;

  List<PodcastEpisode> _cachedEpisodes = [];
  List<PodcastEpisode> get cachedEpisodes => _cachedEpisodes;

  DateTime? _lastRefreshed;
  DateTime? get lastRefreshed => _lastRefreshed;

  Future<void> loadFromCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final episodesJson = prefs.getString(_cacheKeyEpisodes);
      final lastRefreshedStr = prefs.getString(_cacheKeyLastRefreshed);

      if (episodesJson != null) {
        final List<dynamic> decoded = json.decode(episodesJson);
        _cachedEpisodes = decoded
            .map((e) => PodcastEpisode.fromJson(e as Map<String, dynamic>))
            .toList();
        _episodesController.add(_cachedEpisodes);
      }

      if (lastRefreshedStr != null) {
        _lastRefreshed = DateTime.parse(lastRefreshedStr);
        _lastRefreshedController.add(_lastRefreshed);
      }
    } catch (e) {
      debugPrint('Error loading from cache: $e');
    }
  }

  Future<void> _saveToCache(List<PodcastEpisode> episodes) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final episodesJson = json.encode(
        episodes.map((e) => e.toJson()).toList(),
      );
      await prefs.setString(_cacheKeyEpisodes, episodesJson);

      final now = DateTime.now();
      await prefs.setString(_cacheKeyLastRefreshed, now.toIso8601String());

      _lastRefreshed = now;
      _lastRefreshedController.add(_lastRefreshed);
    } catch (e) {
      debugPrint('Error saving to cache: $e');
    }
  }

  Future<void> fetchEpisodes() async {
    _loadingController.add(true);
    _errorController.add(null);

    try {
      debugPrint('Fetching podcast RSS feed: $_feedUrl');
      final response = await http.get(Uri.parse(_feedUrl));

      if (response.statusCode != 200) {
        throw Exception('HTTP ${response.statusCode}');
      }

      final document = XmlDocument.parse(response.body);
      final items = document.findAllElements('item');

      final episodes = <PodcastEpisode>[];
      for (final item in items) {
        try {
          final title = item.getElement('title')?.innerText ?? '';
          final guid = item.getElement('guid')?.innerText ?? '';
          final pubDate = item.getElement('pubDate')?.innerText;
          final enclosure = item.getElement('enclosure');
          final mediaUrl = enclosure?.getAttribute('url') ?? '';
          final durationStr =
              item.getElement('itunes:duration')?.innerText ?? '0';

          if (guid.isEmpty || mediaUrl.isEmpty) continue;

          episodes.add(PodcastEpisode(
            id: guid,
            title: title,
            published: pubDate != null ? _parseRfc2822(pubDate) : DateTime.now(),
            durationSeconds: _parseDuration(durationStr),
            mediaUrl: mediaUrl,
          ));
        } catch (e) {
          debugPrint('Error parsing RSS item: $e');
        }
      }

      _cachedEpisodes = episodes;
      _episodesController.add(episodes);
      _loadingController.add(false);

      await _saveToCache(episodes);
    } catch (e) {
      debugPrint('Error fetching episodes: $e');
      _errorController.add('Failed to load episodes: $e');
      _loadingController.add(false);
    }
  }

  /// Parse RSS duration which can be HH:MM:SS, MM:SS, or just seconds
  int _parseDuration(String duration) {
    if (duration.contains(':')) {
      final parts = duration.split(':').map(int.parse).toList();
      if (parts.length == 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
      } else if (parts.length == 2) {
        return parts[0] * 60 + parts[1];
      }
    }
    return int.tryParse(duration) ?? 0;
  }

  /// Parse RFC 2822 date like "Fri, 27 Mar 2026 09:59:58 -0500"
  DateTime _parseRfc2822(String date) {
    const months = {
      'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
      'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
    };

    try {
      // Remove day-of-week prefix if present
      final str = date.contains(',') ? date.split(',')[1].trim() : date.trim();
      final parts = str.split(RegExp(r'\s+'));
      // Expected: DD Mon YYYY HH:MM:SS +/-HHMM
      final day = int.parse(parts[0]);
      final month = months[parts[1]] ?? 1;
      final year = int.parse(parts[2]);
      final timeParts = parts[3].split(':');
      final hour = int.parse(timeParts[0]);
      final minute = int.parse(timeParts[1]);
      final second = timeParts.length > 2 ? int.parse(timeParts[2]) : 0;

      return DateTime.utc(year, month, day, hour, minute, second);
    } catch (e) {
      debugPrint('Error parsing date "$date": $e');
      return DateTime.now();
    }
  }

  void dispose() {
    _episodesController.close();
    _loadingController.close();
    _errorController.close();
    _lastRefreshedController.close();
  }
}
