import 'package:flutter/foundation.dart';
import '../models/podcast_episode.dart';

/// Podcast picks: what the Pi has saved, plus the user's unsent edits.
///
/// Edits stay local until [submitted] is called, so ticking episodes doesn't
/// start a download per tap, and nothing is sent until the Pi's current list
/// has arrived ([loaded]); sending before then would replace the Pi's picks
/// with whatever happened to be ticked locally.
///
/// Each pick also has a start part: the part the user has reached. The Pi
/// leaves the parts before it off the player, so the player starts there.
class SelectionController extends ChangeNotifier {
  /// Episodes the Pi has saved, keyed by id. Null until its list arrives.
  Map<String, PodcastEpisode>? _server;
  Set<String> _draft = {};

  /// Start parts above 1, as the Pi has them and as edited. Absent means 1.
  Map<String, int> _serverStart = {};
  Map<String, int> _draftStart = {};

  /// How many parts the Pi split each episode into, once it has.
  Map<String, int> _partCounts = {};

  /// Waiting for the Pi to confirm a submit.
  bool _awaitingConfirmation = false;

  bool get loaded => _server != null;
  bool get awaitingConfirmation => _awaitingConfirmation;
  Set<String> get draftIds => Set.unmodifiable(_draft);
  Set<String> get serverIds => _server?.keys.toSet() ?? const {};

  bool isSelected(String id) => _draft.contains(id);

  int startPart(String id) => _draftStart[id] ?? 1;

  /// Null until the Pi has downloaded and split the episode.
  int? partCount(String id) => _partCounts[id];

  bool get hasChanges => loaded && changeCount > 0;

  /// Picks added or removed, plus kept picks whose start part changed.
  int get changeCount {
    final server = serverIds;
    final moved = _draft
        .intersection(server)
        .where((id) => startPart(id) != (_serverStart[id] ?? 1))
        .length;
    return _draft.difference(server).length + server.difference(_draft).length + moved;
  }

  void toggle(String id) {
    if (!loaded) return;
    if (_draft.remove(id)) {
      _draftStart.remove(id);
    } else {
      _draft.add(id);
      if (_serverStart[id] case final part?) _draftStart[id] = part;
    }
    notifyListeners();
  }

  /// Set the part to start from, kept between 1 and the part count when known.
  void setStartPart(String id, int part) {
    if (!loaded || !_draft.contains(id)) return;
    final count = _partCounts[id];
    var clamped = part < 1 ? 1 : part;
    if (count != null && clamped > count) clamped = count;
    if (clamped == 1) {
      _draftStart.remove(id);
    } else {
      _draftStart[id] = clamped;
    }
    notifyListeners();
  }

  void discardChanges() {
    _draft = serverIds;
    _draftStart = Map.of(_serverStart);
    notifyListeners();
  }

  /// Apply the Pi's list (an episodes-to-sync response).
  ///
  /// Returns true when it confirms a pending submit.
  bool applyServerList(List<dynamic> entries) {
    final server = <String, PodcastEpisode>{};
    final serverStart = <String, int>{};
    final partCounts = <String, int>{};
    for (final entry in entries) {
      if (entry is Map<String, dynamic> && entry['id'] is String) {
        final episode = PodcastEpisode.fromSyncJson(entry);
        server[episode.id] = episode;
        if (entry['start_part'] case final int part when part > 1) {
          serverStart[episode.id] = part;
        }
        if (entry['part_count'] case final int count) partCounts[episode.id] = count;
      }
    }
    final wasEditing = hasChanges && !_awaitingConfirmation;
    _server = server;
    _serverStart = serverStart;
    _partCounts = partCounts;

    var confirmed = false;
    if (_awaitingConfirmation &&
        setEquals(_draft, server.keys.toSet()) &&
        mapEquals(_draftStart, serverStart)) {
      _awaitingConfirmation = false;
      confirmed = true;
    }
    // Keep in-progress edits; otherwise mirror the Pi.
    if (!wasEditing && !_awaitingConfirmation) {
      _draft = server.keys.toSet();
      _draftStart = Map.of(serverStart);
    }
    notifyListeners();
    return confirmed;
  }

  /// The full list to publish: every picked episode, with feed data where the
  /// feed has it and the Pi's saved data for picks no longer in the feed.
  List<PodcastEpisode> payload(Iterable<PodcastEpisode> feed) {
    final byId = {for (final e in feed) e.id: e};
    final server = _server ?? const {};
    return [
      for (final id in _draft)
        if (byId[id] ?? server[id] case final episode?) episode,
    ]..sort((a, b) => a.published.compareTo(b.published));
  }

  /// [payload] as the JSON the Pi expects, with each pick's start part.
  List<Map<String, dynamic>> payloadJson(Iterable<PodcastEpisode> feed) {
    return [
      for (final episode in payload(feed)) episode.toSyncJson(startPart: startPart(episode.id)),
    ];
  }

  /// Picked episodes to show at the top of the list, newest first.
  List<PodcastEpisode> selectedEpisodes(Iterable<PodcastEpisode> feed) {
    return payload(feed).reversed.toList();
  }

  void submitted() {
    _awaitingConfirmation = true;
    notifyListeners();
  }

  /// The Pi didn't confirm in time; keep the edits so they can be resent.
  void confirmationTimedOut() {
    _awaitingConfirmation = false;
    notifyListeners();
  }
}
