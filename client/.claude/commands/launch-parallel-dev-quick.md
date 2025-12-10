---
allowed-tools: Bash(git checkout:*), Bash(git branch:*), Bash(mkdir:*), Bash(git add:*), Bash(git commit:*), Bash(cp:*), Bash(ls:*), Bash(powershell -Command:*), Bash(git worktree:*), Bash(Start-Process:*)
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

## Execute These Steps (No Pauses)

### Step 1: Determine feature name
If `$ARGUMENTS` is empty, derive a name from the most recent plan filename (strip random suffixes) and confirm with user.

### Step 2: Create feature branch and plan directory
```bash
git checkout -b features/[feature-name]
mkdir -p plans/[feature-name]
```

### Step 3: Copy plan file
```powershell
powershell -Command "Copy-Item -Path (Get-ChildItem -Path ~\.claude\plans -Filter *.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Destination 'plans/[feature-name]/plan.md'"
```

### Step 4: Commit immediately (no export)
```bash
git add plans/[feature-name]/
git commit -m "Add implementation plan for [feature-name]"
```

### Step 5: Create worktree branches
```bash
git branch features/[feature-name]-claude
git branch features/[feature-name]-codex
```

### Step 6: Create worktrees
```bash
git worktree add ../client-[feature-name]-claude features/[feature-name]-claude
git worktree add ../client-[feature-name]-codex features/[feature-name]-codex
```

### Step 7: Launch terminals with auto-start AIs
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '../client-[feature-name]-claude'; Write-Host '=== CLAUDE CODE ===' -ForegroundColor Cyan; Write-Host 'Starting Claude Code with plan...' -ForegroundColor Yellow; claude --print 'Implement the feature described in @plans/[feature-name]/plan.md'"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '../client-[feature-name]-codex'; Write-Host '=== CODEX ===' -ForegroundColor Green; Write-Host 'Starting Codex with plan...' -ForegroundColor Yellow; codex 'Review and implement the feature described in plans/[feature-name]/plan.md'"
```

### Step 8: Print summary
```
DONE! Parallel development launched (quick mode - no conversation export).

Branches created:
  - features/[feature-name] (base)
  - features/[feature-name]-claude
  - features/[feature-name]-codex

Worktrees:
  - ../client-[feature-name]-claude (Claude Code)
  - ../client-[feature-name]-codex (Codex)

Both AIs are now implementing the plan in parallel.
```
