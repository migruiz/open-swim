# Feature Discard - Cleanup feature branches and worktrees
# Usage: feature-discard.ps1 feature-name

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Feature
)

$ErrorActionPreference = "Stop"

# Get git root and repo name
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    Write-Error "Not in a git repository"
    exit 1
}
$repoRoot = $repoRoot -replace '/', '\'
$repoName = Split-Path $repoRoot -Leaf
$worktreesDir = "$repoRoot\..\$repoName-worktrees"

# Save current branch
$currentBranch = git rev-parse --abbrev-ref HEAD 2>$null

Write-Host ""
Write-Host "=== Feature Discard ==="
Write-Host "Feature: $Feature"
Write-Host "Repo: $repoName"
Write-Host "Current branch: $currentBranch"
Write-Host ""

# Check if we're on a feature branch that will be deleted
$featureBranches = @(
    "features/$Feature/base",
    "features/$Feature/claude",
    "features/$Feature/codex"
)

if ($currentBranch -in $featureBranches) {
    Write-Host "Switching away from feature branch..."
    $switched = $false

    # Try main first, then master
    git checkout main 2>$null
    if ($LASTEXITCODE -eq 0) {
        $switched = $true
    } else {
        git checkout master 2>$null
        if ($LASTEXITCODE -eq 0) {
            $switched = $true
        }
    }

    if (-not $switched) {
        Write-Error "Could not switch to main or master branch"
        exit 1
    }

    # Update saved branch to main/master since original will be deleted
    $currentBranch = git rev-parse --abbrev-ref HEAD 2>$null
}

# Step 1: Remove worktrees
Write-Host "[1/3] Removing worktrees..."
$claudeWorktree = "$worktreesDir\$Feature-claude"
$codexWorktree = "$worktreesDir\$Feature-codex"

if (Test-Path $claudeWorktree) {
    git worktree remove $claudeWorktree 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Warning: Could not remove $Feature-claude worktree. Terminal may still be open."
        git worktree remove --force $claudeWorktree 2>$null
    } else {
        Write-Host "  Removed $Feature-claude worktree"
    }
} else {
    Write-Host "  $Feature-claude worktree not found, skipping"
}

if (Test-Path $codexWorktree) {
    git worktree remove $codexWorktree 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Warning: Could not remove $Feature-codex worktree. Terminal may still be open."
        git worktree remove --force $codexWorktree 2>$null
    } else {
        Write-Host "  Removed $Feature-codex worktree"
    }
} else {
    Write-Host "  $Feature-codex worktree not found, skipping"
}

# Step 2: Delete branches
Write-Host "[2/3] Deleting branches..."
foreach ($branch in $featureBranches) {
    git branch -D $branch 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Deleted $branch"
    } else {
        Write-Host "  $branch not found, skipping"
    }
}

# Step 3: Return to previous branch
Write-Host "[3/3] Returning to previous branch..."
git checkout $currentBranch 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Warning: Could not return to $currentBranch, staying on current branch"
}

Write-Host ""
Write-Host "=== DONE ==="
Write-Host "Feature '$Feature' has been discarded."
Write-Host "Note: plans/$Feature/ folder was kept."
Write-Host ""
