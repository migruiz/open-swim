# Parallel AI Development Workflow

Slash commands for running Claude Code and OpenAI Codex in parallel to implement the same feature.

## Commands

| Command | Description |
|---------|-------------|
| `/launch-parallel-dev` | Full workflow - pauses for conversation export |
| `/launch-parallel-dev-quick` | Quick workflow - plan only, no pauses |

## Workflow Overview

```
┌─────────────────────┐
│  Plan in Claude Code │
│    (plan mode)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ /launch-parallel-dev │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│ Claude  │ │  Codex  │
│ Code    │ │         │
│ Terminal│ │ Terminal│
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│ Commit  │ │ Commit  │
└─────────┘ └─────────┘
```

## Example Usage

### Quick Mode (Recommended for testing)

```bash
# After planning a feature in Claude Code plan mode:
/launch-parallel-dev-quick log-viewer
```

This runs without pauses and:
1. Creates branch `features/log-viewer`
2. Copies plan from `~/.claude/plans/` to `plans/log-viewer/plan.md`
3. Commits the plan
4. Creates branches `features/log-viewer/claude` and `features/log-viewer/codex`
5. Creates worktrees at `../client-log-viewer-claude` and `../client-log-viewer-codex`
6. Opens two PowerShell terminals
7. Auto-starts Claude Code and Codex with the plan context

### Full Mode (With conversation history)

```bash
/launch-parallel-dev log-viewer
```

Same as quick mode, but pauses to let you run:
```bash
/export plans/log-viewer/conversation.md
```

This saves the full planning conversation for richer context.

## Directory Structure After Running

```
C:\repos\open-swim\
├── client\                           # Main repo (you are here)
│   ├── .claude\commands\             # These slash commands
│   └── plans\
│       └── log-viewer\
│           ├── plan.md               # Implementation plan
│           └── conversation.md       # Planning conversation (full mode only)
│
├── client-log-viewer-claude\         # Claude Code worktree
│   └── (full repo on features/log-viewer/claude branch)
│
└── client-log-viewer-codex\          # Codex worktree
    └── (full repo on features/log-viewer/codex branch)
```

## Git Branches Created

- `features/{name}` - Base branch with plan committed
- `features/{name}/claude` - Claude Code implementation branch
- `features/{name}/codex` - Codex implementation branch

## After Implementation

Commit in each terminal when done:

**Claude terminal:**
```bash
git add . && git commit -m "Implement {feature} (Claude)"
```

**Codex terminal:**
```bash
git add . && git commit -m "Implement {feature} (Codex)"
```

## Comparing Results

```bash
# Diff between implementations
git diff features/{name}/claude features/{name}/codex

# Or create PRs from each branch to compare in GitHub
```

## Cleanup Worktrees

When done with parallel development:
```bash
git worktree remove ../client-{name}-claude
git worktree remove ../client-{name}-codex
```
