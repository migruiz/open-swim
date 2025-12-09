# Module 1: MQTT Stability

## Overview

Add reconnection logic with exponential backoff and reactive connection state management.

## Files to Modify

- `lib/services/mqtt_service.dart` - Core reconnection logic
- `lib/main.dart` - Reactive connection UI

## Implementation

### mqtt_service.dart Changes

1. Add `MqttConnectionState` enum (disconnected, connecting, connected)
2. Add connection state stream for reactive UI updates
3. Add reconnection with exponential backoff (1s, 2s, 4s... max 30s)
4. Track subscribed topics for re-subscription after reconnect
5. Add `reconnect()` method for manual retry

### main.dart Changes

1. Replace `bool _isConnected` with reactive state subscription
2. Update UI to show connecting/connected/disconnected states
3. Make status indicator tappable for manual reconnect

## Reconnection Flow

```
disconnected --> connect() --> connecting
                                  |
                    +-------------+-------------+
                    |                           |
                 success                     failure
                    |                           |
                connected              _scheduleReconnect()
                    |                           |
           [connection drops]          Timer(1s, 2s, 4s...)
                    |                           |
            _onDisconnected()                   |
                    |                           |
              disconnected <--------------------+
```

## Status

- [x] Plan created
- [x] mqtt_service.dart updated
- [x] main.dart updated
- [ ] Tested
