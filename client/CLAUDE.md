# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flutter client for **Open Swim** - a personal app to control what podcast episodes and YouTube playlists get synced to an MP3 player. The syncing logic is handled by the API (see `../api/CLAUDE.md`). This client sends sync requests via MQTT and displays logs/status from the API.

**Key Features:**
- Send podcast episodes to sync (JSON payload to MQTT)
- Send YouTube playlists to sync (JSON payload to MQTT)
- Display logs from the API
- Stable MQTT connection with auto-reconnect

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

| Topic | Direction | Payload |
|-------|-----------|---------|
| `openswim/episodes_to_sync` | Client → API | `[{id, date, title, download_url}, ...]` |
| `openswim/playlists_to_sync` | Client → API | `[{id, title}, ...]` |
| `openswim/logs` | API → Client | `{source, level, message, timestamp}` |
| `openswim/device/status` | Bidirectional | Status messages |

## Implementation Modules

See `plans/` folder for detailed implementation plans:
1. **Module 1: MQTT Stability** - Reconnection logic (completed)
2. **Module 2: Log Viewer Widget** - Display app + API logs
3. **Module 3: Send Buttons** - Hardcoded payloads for episodes and playlists
