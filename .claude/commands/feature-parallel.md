---
allowed-tools: Bash(powershell -Command:*)
argument-hint: plan-file-path (optional)
description: Launch parallel dev with Claude and Codex (uses plan file from /plan-feature)
---

# Feature Parallel

Launches parallel development with Claude Code and OpenAI Codex in separate git worktrees.

```bash
powershell -Command "& ((git rev-parse --show-toplevel) + '\.claude\commands\feature-parallel.bat') '$ARGUMENTS'"
```

**Prerequisites:** Run `/plan-feature` first to create a plan with FEATURE_NAME, BRIEF, and PLAN sections.

**Arguments:**
- With path: Uses the specified plan file (e.g., `/feature-parallel C:\Users\...\.claude\plans\my-plan.md`)
- Without argument: Auto-detects the most recently modified `.md` file in `~/.claude/plans/`

The script will:
1. Parse the plan file to extract FEATURE_NAME, BRIEF, and PLAN sections
2. Validate all required markers exist (`<!-- FEATURE_NAME: -->`, `<!-- BEGIN_BRIEF -->`, etc.)
3. Create branch `features/[feature]/base`
4. Create `plans/[feature]/` directory in the repo
5. Extract and write brief.md and plan.md from the parsed sections
6. Commit the plan files
7. Create branches `features/[feature]/claude` and `features/[feature]/codex`
8. Create worktrees in `../[repo-name]-worktrees/`
9. Open PowerShell terminals with initial prompts that:
   - Reference @plans/[feature]/brief.md and @plans/[feature]/plan.md
   - Instruct implementers to VALIDATE the plan before coding
   - Wait for confirmation before implementation
