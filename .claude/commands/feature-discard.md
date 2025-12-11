---
allowed-tools: Bash(powershell -ExecutionPolicy Bypass -File:*)
argument-hint: feature-name
description: Cleanup feature branches and worktrees created by feature-parallel
---

# Feature Discard

Removes branches and worktrees for a feature created by `/feature-parallel`.

```bash
powershell -ExecutionPolicy Bypass -File "$(git rev-parse --show-toplevel)\.claude\commands\feature-discard.ps1" "$ARGUMENTS"
```

The script will:
1. Remove worktrees: `[repo]-worktrees/[feature]-claude` and `[feature]-codex`
2. Delete branches: `features/[feature]/base`, `/claude`, `/codex`
3. Return to the previous branch

Note: The `plans/[feature]/` folder is kept.
