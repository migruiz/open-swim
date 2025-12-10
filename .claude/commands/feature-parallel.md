---
allowed-tools: Bash(powershell -Command:*)
argument-hint: feature-name
description: Launch parallel dev with Claude and Codex in separate worktrees
---

# Feature Parallel

Launches parallel development with Claude Code and OpenAI Codex in separate git worktrees.

```bash
powershell -Command "& '$(git rev-parse --show-toplevel)\.claude\commands\feature-parallel.bat' '$ARGUMENTS'"
```

The script will:
1. Create branch `features/[feature]/base`
2. Create `plans/[feature]/` directory
3. Copy most recent plan from `~/.claude/plans/`
4. Commit the plan
5. Create branches `features/[feature]/claude` and `features/[feature]/codex`
6. Create worktrees in `../[repo-name]-worktrees/`
7. Open PowerShell terminals with titles, cd to correct path, run `claude` and `codex`
