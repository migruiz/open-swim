# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flutter client for **Open Swim** - a personal app to control what podcast episodes and YouTube playlists get synced to an MP3 player. The syncing logic is handled by the API (see `../api/CLAUDE.md`). This client sends sync requests via MQTT and displays logs/status from the API.

**Key Features:**
- Pick podcast episodes for the player and Submit them to the Pi
- Show which videos of each synced YouTube playlist go on the player
- Show the player's state (plugged in / safe to unplug) and the last sync's outcome
- Stable MQTT connection with auto-reconnect and dead-connection detection

## Common Commands

This project uses **FVM** (Flutter Version Management). Prefix all flutter commands with `fvm`:

```bash
# Install dependencies
fvm flutter pub get

# Run the app
fvm flutter run

# Run tests
fvm flutter test

# Run a single test file
fvm flutter test test/widget_test.dart

# Analyze code (linting)
fvm flutter analyze

# Build for release
fvm flutter build apk        # Android
fvm flutter build ios        # iOS
fvm flutter build windows    # Windows
```

## Architecture

- **Entry point**: `lib/main.dart` - Contains `MyApp` widget and `MyHomePage` stateful widget
- **Services**: `lib/services/` - Service classes for external integrations
  - `mqtt_service.dart` - MQTT client with auto-reconnect and connection state management

### MQTT Service Pattern

The `MqttService` uses reactive streams for both messages and connection state:

```dart
// Listen to connection state changes
_mqttService.connectionState.listen((state) {
  // AppMqttConnectionState: disconnected, connecting, connected
});

// Listen to incoming messages
_mqttService.messages.listen((message) {
  // Handle incoming message
});

// Manual reconnect (resets backoff timer)
_mqttService.reconnect();
```

**Connection Features:**
- Auto-reconnect with exponential backoff (1s, 2s, 4s... max 30s)
- Topic tracking - automatically re-subscribes after reconnect
- Connection state stream for reactive UI updates

**MQTT Configuration:**
- Protocol: MQTT v3.1.1 over WebSocket (port 443)
- QoS: `atLeastOnce` for subscriptions and publishing

## Key Dependencies

- `mqtt_client` - MQTT protocol client for device communication
- `flutter_lints` - Linting rules (see `analysis_options.yaml`)

## MQTT Topics

Constants live in `Topics` in `lib/services/mqtt_service.dart`; the server side is `api/src/open_swim/app.py`.

| Topic | Direction | Payload |
|-------|-----------|---------|
| `openswim/episodes_to_sync` | Client → Pi | Full list `[{id, date, title, download_url}, ...]`, sent only on Submit |
| `openswim/episodes-to-sync/request` → `/response` | Client ↔ Pi | Pi's saved picks (same shape); also used to confirm a Submit |
| `openswim/playlists-to-sync/request` → `/response` | Client ↔ Pi | `[{id, title}, ...]` playlists the Pi syncs (one tab each) |
| `openswim/playlist-info/request` → `/response` | Client ↔ Pi | `{playlist_id}` → `{success, playlist_id, title, videos: [{id, title}], error}` (oldest first) |
| `openswim/device/status` | Pi → Client (retained) | `{status: connected\|safe_to_unplug\|disconnected, device, timestamp}` |
| `openswim/sync/progress` | Pi → Client (retained) | `{stages: [{name, label, status, error}], timestamp}` |

## Podcast picks

`SelectionController` (`lib/state/`) owns the picks: the Pi's saved list plus unsent edits. Episodes from the RSS feed carry no selection state, so reloading the feed can't clear picks. Ticking is disabled until the Pi's list has arrived, edits are sent only with Submit (disabled while disconnected), and a Submit counts as saved only when the Pi's list comes back matching.

## Releases

Push a `vX.Y.Z` tag: `.github/workflows/build-android.yml` builds a signed APK versioned from the tag and attaches it to a GitHub release, which the in-app update banner offers. Keep `version:` in `pubspec.yaml` in step for local builds.

## Implementation Modules

See `plans/` folder for detailed implementation plans:
1. **Module 1: MQTT Stability** - Reconnection logic (completed)
2. **Module 2: Log Viewer Widget** - Display app + API logs
3. **Module 3: Send Buttons** - Hardcoded payloads for episodes and playlists
