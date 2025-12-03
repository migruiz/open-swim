# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Flutter client for Open Swim, an IoT/device management application that communicates with devices via MQTT over WebSocket.

## Common Commands

```bash
# Install dependencies
flutter pub get

# Run the app
flutter run

# Run tests
flutter test

# Run a single test file
flutter test test/widget_test.dart

# Analyze code (linting)
flutter analyze

# Build for release
flutter build apk        # Android
flutter build ios        # iOS
flutter build windows    # Windows
```

## Architecture

- **Entry point**: `lib/main.dart` - Contains `MyApp` widget and `MyHomePage` stateful widget
- **Services**: `lib/services/` - Service classes for external integrations
  - `mqtt_service.dart` - MQTT client for device communication over WebSocket (wss://)

## Key Dependencies

- `mqtt_client` - MQTT protocol client for device communication
- `flutter_lints` - Linting rules (see `analysis_options.yaml`)

## MQTT Topics

The app uses these MQTT topic patterns:
- `openswim/device/status` - Device status updates (subscribe and publish)
