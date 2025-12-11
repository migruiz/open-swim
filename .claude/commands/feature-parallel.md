---
allowed-tools: Bash(powershell -ExecutionPolicy Bypass -File:*)
description: Launch parallel dev with Claude and Codex (uses plan file from /plan-feature)
---

# Feature Parallel

Launches parallel development with Claude Code and OpenAI Codex in separate git worktrees.

```bash
powershell -ExecutionPolicy Bypass -File "$(git rev-parse --show-toplevel)\.claude\commands\feature-parallel.ps1"
```

**Prerequisites:** Run `/plan-feature` first to create a plan with FEATURE_NAME, BRIEF, and PLAN sections.

Auto-detects the most recently modified `.md` file in `~/.claude/plans/`.

The script will:
1. Parse the plan file to extract FEATURE_NAME, BRIEF, and PLAN sections
2. Validate all required markers exist
3. Create branch `features/[feature]/base`
4. Create `plans/[feature]/` directory and extract brief.md + plan.md
5. Commit the plan files
6. Create branches `features/[feature]/claude` and `features/[feature]/codex`
7. Create worktrees in `../[repo-name]-worktrees/`
8. Open PowerShell terminals with initial prompts
