---
allowed-tools: Bash(git checkout:*), Bash(git branch:*), Bash(mkdir:*), Bash(git add:*), Bash(git commit:*), Bash(cp:*), Bash(ls:*), Bash(powershell -Command:*), Bash(git worktree:*)
argument-hint: feature-name
description: Quick parallel dev setup - skip export, just use plan file
---

# Launch Parallel Development (Quick)

Single command to set up parallel Claude/Codex development WITHOUT conversation export.
Use this when you just want to use the plan file without the full conversation history.

## Context

- Feature name: `$ARGUMENTS`
- Recent plans in ~/.claude/plans/: !`powershell -Command "Get-ChildItem -Path ~\.claude\plans -Filter *.md | Sort-Object LastWriteTime -Descending | Select-Object -First 3 -ExpandProperty Name"`
- Current branch: !`git branch --show-current`
- Git root: !`git rev-parse --show-toplevel`
- Current relative path: !`powershell -Command "Push-Location (git rev-parse --show-toplevel); [System.IO.Path]::GetRelativePath((Get-Location), '$(Get-Location)') -replace '^\.$','.'; Pop-Location"`

## Execute These Steps (No Pauses)

### Step 1: Determine feature name
If `$ARGUMENTS` is empty, derive a name from the most recent plan filename (strip random suffixes) and confirm with user.

### Step 2: Detect paths
Detect the following and store them for use in subsequent steps:
- REPO_ROOT: git root directory
- REPO_NAME: basename of git root (e.g., "open-swim")
- RELATIVE_PATH: current directory relative to git root (e.g., "client" or "api")
- WORKTREES_DIR: ../[REPO_NAME]-worktrees

### Step 3: Create feature base branch and plan directory
```bash
git checkout -b features/[feature-name]/base
mkdir -p plans/[feature-name]
```

### Step 4: Copy plan file
Copy the most recent plan from ~/.claude/plans/ to plans/[feature-name]/plan.md

### Step 5: Commit immediately (no export)
```bash
git add plans/[feature-name]/
git commit -m "Add implementation plan for [feature-name]"
```

### Step 6: Create worktree branches
```bash
git branch features/[feature-name]/claude
git branch features/[feature-name]/codex
```

### Step 7: Create worktrees folder and worktrees
```bash
mkdir -p ../[REPO_NAME]-worktrees
git worktree add ../[REPO_NAME]-worktrees/[feature-name]-claude features/[feature-name]/claude
git worktree add ../[REPO_NAME]-worktrees/[feature-name]-codex features/[feature-name]/codex
```

### Step 8: Launch terminals with AIs
Open two PowerShell terminals with custom window titles:
- Claude terminal: Title "[feature-name]-claude", cd to worktree/[RELATIVE_PATH], run `claude`
- Codex terminal: Title "[feature-name]-codex", cd to worktree/[RELATIVE_PATH], run `codex`

Use this pattern (wrap Start-Process in powershell -Command):
```bash
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', '$$host.UI.RawUI.WindowTitle = ''[feature-name]-claude''; cd ''[WORKTREES_DIR]/[feature-name]-claude/[RELATIVE_PATH]''; claude'"
```

### Step 9: Print summary
```
DONE! Parallel development launched (quick mode - no conversation export).

Branches created:
  - features/[feature-name]/base (base branch with plan)
  - features/[feature-name]/claude
  - features/[feature-name]/codex

Worktrees:
  - ../[REPO_NAME]-worktrees/[feature-name]-claude
  - ../[REPO_NAME]-worktrees/[feature-name]-codex

Terminals opened in: [RELATIVE_PATH]
Terminal titles: [feature-name]-claude, [feature-name]-codex

Both AIs are now ready for implementation.
```
