import 'package:flutter/foundation.dart';
import '../models/podcast_episode.dart';

/// Podcast picks: what the Pi has saved, plus the user's unsent edits.
///
/// Edits stay local until [submitted] is called, so ticking episodes doesn't
/// start a download per tap, and nothing is sent until the Pi's current list
/// has arrived ([loaded]); sending before then would replace the Pi's picks
/// with whatever happened to be ticked locally.
class SelectionController extends ChangeNotifier {
  /// Episodes the Pi has saved, keyed by id. Null until its list arrives.
  Map<String, PodcastEpisode>? _server;
  Set<String> _draft = {};

  /// Waiting for the Pi to confirm a submit.
  bool _awaitingConfirmation = false;

  bool get loaded => _server != null;
  bool get awaitingConfirmation => _awaitingConfirmation;
  Set<String> get draftIds => Set.unmodifiable(_draft);
  Set<String> get serverIds => _server?.keys.toSet() ?? const {};

  bool isSelected(String id) => _draft.contains(id);

  bool get hasChanges => loaded && !setEquals(_draft, serverIds);

  /// Picks added or removed relative to the Pi's list.
  int get changeCount {
    final server = serverIds;
    return _draft.difference(server).length + server.difference(_draft).length;
  }

  void toggle(String id) {
    if (!loaded) return;
    if (!_draft.remove(id)) _draft.add(id);
    notifyListeners();
  }

  void discardChanges() {
    _draft = serverIds;
    notifyListeners();
  }

  /// Apply the Pi's list (an episodes-to-sync response).
  ///
  /// Returns true when it confirms a pending submit.
  bool applyServerList(List<dynamic> entries) {
    final server = <String, PodcastEpisode>{};
    for (final entry in entries) {
      if (entry is Map<String, dynamic> && entry['id'] is String) {
        final episode = PodcastEpisode.fromSyncJson(entry);
        server[episode.id] = episode;
      }
    }
    final wasEditing = hasChanges && !_awaitingConfirmation;
    _server = server;

    var confirmed = false;
    if (_awaitingConfirmation && setEquals(_draft, server.keys.toSet())) {
      _awaitingConfirmation = false;
      confirmed = true;
    }
    // Keep in-progress edits; otherwise mirror the Pi.
    if (!wasEditing && !_awaitingConfirmation) {
      _draft = server.keys.toSet();
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
