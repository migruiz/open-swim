---
allowed-tools: Bash(powershell -Command:*)
argument-hint: feature-name
description: Cleanup feature branches and worktrees created by feature-parallel
---

# Feature Discard

Removes branches and worktrees for a feature created by `/feature-parallel`.

```bash
powershell -Command "& '$(git rev-parse --show-toplevel)\.claude\commands\feature-discard.bat' '$ARGUMENTS'"
```

The script will:
1. Remove worktrees: `[repo]-worktrees/[feature]-claude` and `[feature]-codex`
2. Delete branches: `features/[feature]/base`, `/claude`, `/codex`
3. Return to the previous branch

Note: The `plans/[feature]/` folder is kept.
