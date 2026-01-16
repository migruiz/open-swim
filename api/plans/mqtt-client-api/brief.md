# Feature Brief: mqtt-client-api

## Problem Statement
The Flutter client needs to interact with the API for two key functionalities:
1. **Fetch YouTube playlist information** - Given a playlist URL or ID, retrieve playlist metadata and video list without triggering a full sync
2. **Monitor sync progress** - Receive real-time updates about sync operations (downloads, normalization, device copy) to display progress to users

Currently, the API only accepts sync requests but doesn't expose playlist info lookup or progress notifications.

## Requirements & Constraints

### Feature 1: Playlist Info Endpoint
- Accept playlist ID or full YouTube URL via MQTT topic `openswim/playlist-info/request`
- Respond asynchronously on `openswim/playlist-info/response`
- Return: playlist id, title, and list of videos (id, title)
- Use existing `fetch_playlist_information()` from yt-dlp
- Handle errors gracefully with error message in response

### Feature 2: Sync Progress Publishing
- Publish all sync progress to `openswim/sync/progress` topic
- Detailed granularity: per-video/file progress with percentages
- Include error details when individual items fail
- Preserve existing console output (print statements)
- Cover all sync phases: youtube_library, podcast_library, device_youtube, device_podcast

### Technical Constraints
- Thread safety: sync runs in worker thread, MQTT client in main thread (paho-mqtt publish is thread-safe)
- Avoid changing function signatures extensively - use module-level accessor pattern
- Progress reporter must be testable (protocol-based abstraction)

## Considered Approaches

| Approach | Description | Pros | Cons | Verdict |
|----------|-------------|------|------|---------|
| A: Progress Reporter Protocol | Create `ProgressReporter` protocol with `MqttProgressReporter` implementation; module-level accessor | Testable, loosely coupled, minimal API changes | New abstraction layer | **Chosen** |
| B: Pass client directly | Thread MqttClient through all sync functions | Simple, explicit | 10+ function signature changes, tight coupling | Rejected |
| C: Event bus | Create pubsub system for progress events | Decoupled, extensible | Over-engineered for this use case | Rejected |

## Key Decisions

1. **Decision**: Use Protocol-based ProgressReporter with module-level accessor
   **Rationale**: Allows sync functions to report progress without changing their signatures; provides `NullProgressReporter` for testing; matches existing `get_device_monitor()` pattern
   **Alternatives rejected**: Direct client passing (too invasive), global singleton (not testable)

2. **Decision**: Single progress topic with `phase` field instead of multiple topics
   **Rationale**: Simplifies client subscription logic; single source of truth for all progress
   **Alternatives rejected**: Separate topics per sync type (more complex client)

3. **Decision**: Keep console print() statements alongside MQTT publishing
   **Rationale**: Preserves existing debugging capability; MQTT publishing is fire-and-forget
   **Alternatives rejected**: Replace prints entirely (loses console visibility)

## Success Criteria
- [ ] Client can send playlist ID/URL and receive playlist info response
- [ ] Progress messages published for each video download/normalize step
- [ ] Progress messages include current_index, total_count, percentage
- [ ] Errors during sync published with error_message field
- [ ] Existing console output preserved
- [ ] Type checking passes (`uv run mypy src/`)

## Open Questions / Risks
- yt-dlp may timeout (60s) for large playlists - client should handle delayed responses
- High-frequency progress messages (QoS 0) may be dropped under network issues - acceptable for progress updates