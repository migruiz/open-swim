# Launch Parallel Development - PowerShell version
# Auto-detects latest .md file in ~/.claude/plans/

$ErrorActionPreference = "Stop"

# Step 1: Auto-detect latest plan file
Write-Host "Auto-detecting latest plan file..."
$planFile = Get-ChildItem "$env:USERPROFILE\.claude\plans\*.md" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $planFile) {
    Write-Error "No plan files found in $env:USERPROFILE\.claude\plans\"
    Write-Host "Run /plan-feature first to create a plan."
    exit 1
}
Write-Host "Using: $($planFile.FullName)"

# Step 2: Parse plan file
Write-Host "Parsing plan file..."
$content = Get-Content $planFile.FullName -Raw

# Extract FEATURE_NAME
$featureMatch = [regex]::Match($content, '<!-- FEATURE_NAME: (.+?) -->')
if (-not $featureMatch.Success) {
    Write-Error "FEATURE_NAME marker not found. Make sure plan contains: <!-- FEATURE_NAME: your-feature -->"
    exit 1
}
$feature = $featureMatch.Groups[1].Value.Trim()
Write-Host "Found feature: $feature"

# Validate markers
if ($content -notmatch '<!-- BEGIN_BRIEF -->') { Write-Error "BEGIN_BRIEF marker not found"; exit 1 }
if ($content -notmatch '<!-- END_BRIEF -->') { Write-Error "END_BRIEF marker not found"; exit 1 }
if ($content -notmatch '<!-- BEGIN_PLAN -->') { Write-Error "BEGIN_PLAN marker not found"; exit 1 }
if ($content -notmatch '<!-- END_PLAN -->') { Write-Error "END_PLAN marker not found"; exit 1 }

# Step 3: Get git info
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    Write-Error "Not in a git repository"
    exit 1
}
$repoRoot = $repoRoot -replace '/', '\'
$repoName = Split-Path $repoRoot -Leaf
$currentDir = Get-Location
$relativePath = if ($currentDir.Path -eq $repoRoot) { "." } else { $currentDir.Path.Replace("$repoRoot\", "") }
$worktreesDir = "$repoRoot\..\$repoName-worktrees"

Write-Host ""
Write-Host "=== Launch Parallel Development ==="
Write-Host "Feature: $feature"
Write-Host "Repo: $repoName"
Write-Host "Relative path: $relativePath"
Write-Host "Plan file: $($planFile.FullName)"
Write-Host ""

# Step 4: Create feature base branch
Write-Host "[1/7] Creating feature branch features/$feature/base..."
git checkout -b "features/$feature/base"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create branch"
    exit 1
}

# Step 5: Create plans directory
Write-Host "[2/7] Creating plans/$feature/ directory..."
New-Item -ItemType Directory -Path "plans\$feature" -Force | Out-Null

# Step 6: Extract and write plan files
Write-Host "[3/7] Extracting plan files..."

$briefMatch = [regex]::Match($content, '(?s)<!-- BEGIN_BRIEF -->(.+?)<!-- END_BRIEF -->')
if ($briefMatch.Success) {
    $briefMatch.Groups[1].Value.Trim() | Set-Content -Path "plans\$feature\brief.md" -Encoding UTF8 -NoNewline
    Write-Host "  - Created brief.md"
} else {
    Write-Error "Failed to extract BRIEF section"
    exit 1
}

$planMatch = [regex]::Match($content, '(?s)<!-- BEGIN_PLAN -->(.+?)<!-- END_PLAN -->')
if ($planMatch.Success) {
    $planMatch.Groups[1].Value.Trim() | Set-Content -Path "plans\$feature\plan.md" -Encoding UTF8 -NoNewline
    Write-Host "  - Created plan.md"
} else {
    Write-Error "Failed to extract PLAN section"
    exit 1
}

# Step 7: Commit
Write-Host "[4/7] Committing plan..."
git add "plans\$feature\"
git commit -m "Add implementation plan for $feature"

# Step 8: Create worktree branches
Write-Host "[5/7] Creating worktree branches..."
git branch "features/$feature/claude"
git branch "features/$feature/codex"

# Step 9: Create worktrees
Write-Host "[6/7] Creating worktrees..."
if (-not (Test-Path $worktreesDir)) {
    New-Item -ItemType Directory -Path $worktreesDir -Force | Out-Null
}
git worktree add "$worktreesDir\$feature-claude" "features/$feature/claude"
git worktree add "$worktreesDir\$feature-codex" "features/$feature/codex"

# Step 10: Open terminals with initial prompts
Write-Host "[7/7] Opening terminals with initial prompts..."
$claudePath = "$worktreesDir\$feature-claude\$relativePath"
$codexPath = "$worktreesDir\$feature-codex\$relativePath"

# Build prompts
$claudePrompt = "You are implementing feature '$feature'. Read @plans/$feature/brief.md for context, requirements and rationale. Read @plans/$feature/plan.md for implementation steps. CRITICAL: Before writing ANY code, you MUST validate the plan: (1) Read both files completely (2) Verify all files referenced in the plan exist (3) Check the approach aligns with existing code patterns (4) Identify any issues, missing deps, or unclear requirements (5) Report validation findings and WAIT for confirmation. Do NOT implement until validation passes. If you find problems, explain them clearly. After validation approval, follow plan.md steps precisely. When implementation is complete, commit all your changes with a descriptive commit message."

$codexPrompt = "You are implementing feature '$feature'. Read @plans/$feature/brief.md for context and rationale. Read @plans/$feature/plan.md for implementation steps. BEFORE CODING: Validate the plan first - (1) Read both files (2) Check referenced files exist (3) Verify approach matches codebase patterns (4) Report any issues found (5) Wait for confirmation before implementing. Only proceed after validation passes. Follow plan.md steps precisely. When implementation is complete, commit all your changes with a descriptive commit message."

# Write prompts to temp files
$claudePromptFile = "$env:TEMP\claude_prompt_$feature.txt"
$codexPromptFile = "$env:TEMP\codex_prompt_$feature.txt"

$claudePrompt | Set-Content -Path $claudePromptFile -Encoding UTF8 -NoNewline
$codexPrompt | Set-Content -Path $codexPromptFile -Encoding UTF8 -NoNewline

# Launch terminals
Start-Process powershell -ArgumentList '-NoExit', '-Command', @"
Set-Location '$claudePath'
`$host.UI.RawUI.WindowTitle = '$feature-claude'
claude --dangerously-skip-permissions (Get-Content '$claudePromptFile' -Raw)
"@

Start-Process powershell -ArgumentList '-NoExit', '-Command', @"
Set-Location '$codexPath'
`$host.UI.RawUI.WindowTitle = '$feature-codex'
codex --ask-for-approval never (Get-Content '$codexPromptFile' -Raw)
"@

Write-Host ""
Write-Host "=== DONE ==="
Write-Host ""
Write-Host "Branches created:"
Write-Host "  - features/$feature/base"
Write-Host "  - features/$feature/claude"
Write-Host "  - features/$feature/codex"
Write-Host ""
Write-Host "Worktrees:"
Write-Host "  - $worktreesDir\$feature-claude"
Write-Host "  - $worktreesDir\$feature-codex"
Write-Host ""
Write-Host "Terminals opened in: $relativePath"
Write-Host ""
