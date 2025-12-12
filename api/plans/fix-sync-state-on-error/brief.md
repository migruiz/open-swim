# Feature Brief: fix-sync-state-on-error

## Problem Statement
When copying files to the MP3 device fails, the sync functions still save the sync state as if everything succeeded. This causes subsequent syncs to skip the playlist/podcast because the state indicates it's "already synced", leaving the device with missing files that never get recovered.

## Requirements & Constraints
- If any file copy fails during device sync, the sync state must NOT be saved
- On next sync, the playlist/podcast should be fully re-processed
- All-or-nothing behavior: either all files copy successfully and state is saved, or nothing is saved
- Exceptions should propagate with meaningful context (which file failed, which playlist/podcast)
- The upper-level exception handler in `sync.py:23` will catch and log the error

## Considered Approaches
| Approach | Description | Pros | Cons | Verdict |
|----------|-------------|------|------|---------|
| Track failures with boolean flag | Add `copy_failed` flag, only save state if False | Simple to implement | Swallows errors, state still uncertain | Rejected |
| Remove try/except entirely | Let exceptions propagate naturally | Very simple | Lose context about which file/playlist failed | Rejected |
| Catch and re-raise | Catch exception, add context, re-raise | Preserves context, clean propagation | Slightly more code | **Chosen** |

## Key Decisions
1. **Decision**: Catch exceptions during file copy, wrap with additional context, and re-raise
   **Rationale**: This provides meaningful error messages (which file, which playlist) while ensuring the sync state is never saved on failure
   **Alternatives rejected**: Silent failure tracking (swallows errors), no try/except (loses context)

2. **Decision**: All-or-nothing per playlist/podcast
   **Rationale**: Simpler than tracking partial success, ensures device state matches sync state
   **Alternatives rejected**: Partial success tracking (adds complexity, harder to debug)

## Success Criteria
- [ ] When a file copy fails in YouTube sync, the exception propagates and sync state is NOT updated
- [ ] When a file copy fails in podcast sync, the exception propagates and sync state is NOT updated
- [ ] Error messages include the filename that failed and the playlist/podcast context
- [ ] On next sync after a failure, the affected playlist/podcast is fully re-processed
- [ ] Type checking passes (`uv run mypy src/`)

## Open Questions / Risks
- The podcast sync deletes all existing MP3s before copying new ones (line 59). If copy fails mid-way, the device will have an empty/partial podcast folder until next successful sync. This is existing behavior and not in scope for this fix.