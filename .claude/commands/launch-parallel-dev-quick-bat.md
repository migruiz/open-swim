---
allowed-tools: Bash(cmd /c:*)
argument-hint: feature-name
description: Quick parallel dev setup using .bat script (faster, no AI overhead)
---

# Launch Parallel Development (Quick) - BAT Version

This command runs the `launch-parallel-dev-quick.bat` script directly, without AI involvement.

## Usage

Run the .bat script with the feature name:

```bash
cmd /c "$(git rev-parse --show-toplevel)/.claude/commands/launch-parallel-dev-quick.bat" $ARGUMENTS
```

The script will:
1. Create branch `features/[feature]/base`
2. Create `plans/[feature]/` directory
3. Copy most recent plan from `~/.claude/plans/`
4. Commit the plan
5. Create branches `features/[feature]/claude` and `features/[feature]/codex`
6. Create worktrees in `../[repo-name]-worktrees/`
7. Open PowerShell terminals with titles, cd to correct path, run `claude` and `codex`
