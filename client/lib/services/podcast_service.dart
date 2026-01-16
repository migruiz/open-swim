import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/podcast_episode.dart';

class PodcastService {
  static const String _baseUrl = 'https://podbay.fm/api/podcast';
  static const String _podcastSlug = 'the-billy-madison-show-podcast';
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
      print('Error loading from cache: $e');
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
      print('Error saving to cache: $e');
    }
  }

  Future<void> fetchEpisodes() async {
    _loadingController.add(true);
    _errorController.add(null);

    try {
      // Fetch pages 0 and 1 in parallel
      final results = await Future.wait([
        _fetchPage(0),
        _fetchPage(1),
      ]);

      final allEpisodes = <PodcastEpisode>[];
      for (final pageEpisodes in results) {
        allEpisodes.addAll(pageEpisodes);
      }

      // Remove duplicates based on id
      final seen = <String>{};
      final uniqueEpisodes = allEpisodes.where((e) => seen.add(e.id)).toList();

      _cachedEpisodes = uniqueEpisodes;
      _episodesController.add(uniqueEpisodes);
      _loadingController.add(false);

      // Save to cache after successful fetch
      await _saveToCache(uniqueEpisodes);
    } catch (e) {
      print('Error fetching episodes: $e');
      _errorController.add('Failed to load episodes: $e');
      _loadingController.add(false);
    }
  }

  Future<List<PodcastEpisode>> _fetchPage(int page) async {
    final url = Uri.parse('$_baseUrl?slug=$_podcastSlug&reverse=false&page=$page');
    print('Fetching podcast page $page: $url');

    final response = await http.get(url);

    if (response.statusCode != 200) {
      throw Exception('HTTP ${response.statusCode}');
    }

    final data = json.decode(response.body);
    final podcast = data['podcast'] as Map<String, dynamic>?;
    final episodes = podcast?['episodes'] as List<dynamic>? ?? [];

    return episodes
        .map((e) => PodcastEpisode.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  void updateSelection(String episodeId, bool isSelected) {
    final index = _cachedEpisodes.indexWhere((e) => e.id == episodeId);
    if (index != -1) {
      _cachedEpisodes[index].isSelected = isSelected;
      _episodesController.add(List.from(_cachedEpisodes));
    }
  }

  void applySelectedIds(Set<String> selectedIds) {
    for (final episode in _cachedEpisodes) {
      episode.isSelected = selectedIds.contains(episode.id);
    }
    _episodesController.add(List.from(_cachedEpisodes));
  }

  List<PodcastEpisode> get selectedEpisodes =>
      _cachedEpisodes.where((e) => e.isSelected).toList();

  void dispose() {
    _episodesController.close();
    _loadingController.close();
    _errorController.close();
    _lastRefreshedController.close();
  }
}
