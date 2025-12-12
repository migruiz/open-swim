# Feature Brief: youtube-audio-intro

## Problem Statement
YouTube videos synced to the library lack audio identification. When listening through multiple tracks on the OpenSwim player, users cannot easily identify which video is playing without looking at filenames. The podcast implementation already solves this with audio intros - we need the same for YouTube videos.

## Requirements & Constraints
- Speak the video title at the start of each YouTube MP3
- Use Piper TTS (same as podcast intros) with existing config
- Add 0.5 second silence between intro and video audio
- Always enabled (no feature flag needed)
- Track progress with a new `ADDING_INTRO` status
- Follow the podcast pattern with a dedicated processor module

## Considered Approaches
| Approach | Description | Pros | Cons | Verdict |
|----------|-------------|------|------|---------|
| A - Inline in library_sync.py | Add intro functions directly to library_sync.py | Simple, fewer files | Mixed concerns, harder to test | Rejected |
| B - New intro_processor module | Create youtube/intro_processor.py mirroring podcast pattern | Clean separation, follows existing pattern, reusable | Extra file | Chosen |

## Key Decisions
1. **Decision**: Create new `intro_processor.py` module
   **Rationale**: Follows the established podcast pattern, keeps library_sync focused on orchestration
   **Alternatives rejected**: Inline code would mix TTS/ffmpeg logic with sync orchestration

2. **Decision**: Add `ADDING_INTRO` status to VideoStatus enum
   **Rationale**: Provides visibility into processing progress, consistent with podcast's `INTRO_ADDED` pattern
   **Alternatives rejected**: Keeping existing statuses would hide this processing step

3. **Decision**: Speak title only (no "From YouTube" prefix)
   **Rationale**: User preference - keeps intros concise
   **Alternatives rejected**: Prefixed format would add unnecessary verbosity

## Success Criteria
- [ ] YouTube videos have spoken title intro when played
- [ ] 0.5 second silence separates intro from video content
- [ ] Status shows `ADDING_INTRO` during intro generation
- [ ] Existing podcast intro functionality unchanged
- [ ] Type checking passes (`uv run mypy src/`)

## Open Questions / Risks
- Long video titles may produce lengthy spoken intros (acceptable for now)
- Piper must be available on PATH with configured voice model