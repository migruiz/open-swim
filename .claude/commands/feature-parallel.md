---
allowed-tools: Bash(powershell -Command:*)
argument-hint: feature-name
description: Launch parallel dev with Claude and Codex (requires /plan-feature first)
---

# Feature Parallel

Launches parallel development with Claude Code and OpenAI Codex in separate git worktrees.

```bash
powershell -Command "& '$(git rev-parse --show-toplevel)\.claude\commands\feature-parallel.bat' '$ARGUMENTS'"
```

**Prerequisites:** Run `/plan-feature [feature]` first to create brief.md and plan.md

The script will:
1. Validate plan folder exists at `~/.claude/plans/[feature]/` with brief.md and plan.md
2. Create branch `features/[feature]/base`
3. Create `plans/[feature]/` directory
4. Copy brief.md and plan.md from plan folder
5. Commit the plan files
6. Create branches `features/[feature]/claude` and `features/[feature]/codex`
7. Create worktrees in `../[repo-name]-worktrees/`
8. Open PowerShell terminals with initial prompts that:
   - Reference @plans/[feature]/brief.md and @plans/[feature]/plan.md
   - Instruct implementers to VALIDATE the plan before coding
   - Wait for confirmation before implementation
