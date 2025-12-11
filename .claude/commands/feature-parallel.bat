@echo off
setlocal enabledelayedexpansion

:: Launch Parallel Development (Quick) - .bat version
:: Usage: launch-parallel-dev-quick.bat feature-name

:: Validate argument
if "%~1"=="" (
    echo Usage: launch-parallel-dev-quick.bat feature-name
    exit /b 1
)
set FEATURE=%~1

:: Get git root and repo name
for /f "delims=" %%i in ('git rev-parse --show-toplevel 2^>nul') do set "REPO_ROOT=%%i"
if "%REPO_ROOT%"=="" (
    echo Error: Not in a git repository
    exit /b 1
)

:: Convert forward slashes to backslashes for Windows
set "REPO_ROOT=%REPO_ROOT:/=\%"

:: Get repo name (basename of REPO_ROOT)
for %%i in ("%REPO_ROOT%") do set "REPO_NAME=%%~nxi"

:: Get current directory and relative path from repo root
set "CURRENT_DIR=%CD%"
:: Use PowerShell to get relative path (compatible with .NET Framework)
for /f "delims=" %%i in ('powershell -Command "$root='%REPO_ROOT%'; $curr='%CURRENT_DIR%'; if ($curr -eq $root) { '.' } else { $curr.Replace($root + '\', '') }"') do set "RELATIVE_PATH=%%i"

:: Set worktrees directory
set "WORKTREES_DIR=%REPO_ROOT%\..\%REPO_NAME%-worktrees"

:: Get plan folder for this feature from ~/.claude/plans/[feature]/
set "PLAN_FOLDER=%USERPROFILE%\.claude\plans\%FEATURE%"

:: Validate plan folder exists with required files
if not exist "%PLAN_FOLDER%" (
    echo Error: Plan folder not found: %PLAN_FOLDER%
    echo Run /plan-feature %FEATURE% first to create the plan.
    exit /b 1
)
if not exist "%PLAN_FOLDER%\brief.md" (
    echo Error: brief.md not found in %PLAN_FOLDER%
    exit /b 1
)
if not exist "%PLAN_FOLDER%\plan.md" (
    echo Error: plan.md not found in %PLAN_FOLDER%
    exit /b 1
)

echo.
echo === Launch Parallel Development (Quick) ===
echo Feature: %FEATURE%
echo Repo: %REPO_NAME%
echo Relative path: %RELATIVE_PATH%
echo Plan folder: %PLAN_FOLDER%
echo.

:: Step 1: Create feature base branch
echo [1/7] Creating feature branch features/%FEATURE%/base...
git checkout -b features/%FEATURE%/base
if errorlevel 1 (
    echo Error: Failed to create branch
    exit /b 1
)

:: Step 2: Create plans directory
echo [2/7] Creating plans/%FEATURE%/ directory...
mkdir "plans\%FEATURE%" 2>nul

:: Step 3: Copy plan files (brief + plan)
echo [3/7] Copying plan files...
copy "%PLAN_FOLDER%\brief.md" "plans\%FEATURE%\brief.md" >nul
copy "%PLAN_FOLDER%\plan.md" "plans\%FEATURE%\plan.md" >nul
echo   - Copied brief.md
echo   - Copied plan.md

:: Step 4: Commit
echo [4/7] Committing plan...
git add plans\%FEATURE%\
git commit -m "Add implementation plan for %FEATURE%"

:: Step 5: Create worktree branches
echo [5/7] Creating worktree branches...
git branch "features/%FEATURE%/claude"
git branch "features/%FEATURE%/codex"

:: Step 6: Create worktrees
echo [6/7] Creating worktrees...
if not exist "%WORKTREES_DIR%" mkdir "%WORKTREES_DIR%"
git worktree add "%WORKTREES_DIR%\%FEATURE%-claude" "features/%FEATURE%/claude"
git worktree add "%WORKTREES_DIR%\%FEATURE%-codex" "features/%FEATURE%/codex"

:: Step 7: Open terminals with initial prompts
echo [7/7] Opening terminals with initial prompts...
set "CLAUDE_PATH=%WORKTREES_DIR%\%FEATURE%-claude\%RELATIVE_PATH%"
set "CODEX_PATH=%WORKTREES_DIR%\%FEATURE%-codex\%RELATIVE_PATH%"

:: Build initial prompts for Claude and Codex
set "CLAUDE_PROMPT=You are implementing feature '%FEATURE%' in a parallel dev setup. Read @plans/%FEATURE%/brief.md for context, requirements and rationale. Read @plans/%FEATURE%/plan.md for implementation steps. CRITICAL: Before writing ANY code, you MUST validate the plan: (1) Read both files completely (2) Verify all files referenced in the plan exist (3) Check the approach aligns with existing code patterns (4) Identify any issues, missing deps, or unclear requirements (5) Report validation findings and WAIT for confirmation. Do NOT implement until validation passes. If you find problems, explain them clearly. After validation approval, follow plan.md steps precisely."

set "CODEX_PROMPT=You are implementing feature '%FEATURE%' in a parallel dev setup. Read @plans/%FEATURE%/brief.md for context and rationale. Read @plans/%FEATURE%/plan.md for implementation steps. BEFORE CODING: Validate the plan first - (1) Read both files (2) Check referenced files exist (3) Verify approach matches codebase patterns (4) Report any issues found (5) Wait for confirmation before implementing. Only proceed after validation passes. Follow plan.md steps precisely."

powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', \"cd '%CLAUDE_PATH%'; `$host.UI.RawUI.WindowTitle = '%FEATURE%-claude'; claude '%CLAUDE_PROMPT%'\""
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', \"cd '%CODEX_PATH%'; `$host.UI.RawUI.WindowTitle = '%FEATURE%-codex'; codex '%CODEX_PROMPT%'\""

echo.
echo === DONE ===
echo.
echo Branches created:
echo   - features/%FEATURE%/base
echo   - features/%FEATURE%/claude
echo   - features/%FEATURE%/codex
echo.
echo Worktrees:
echo   - %WORKTREES_DIR%\%FEATURE%-claude
echo   - %WORKTREES_DIR%\%FEATURE%-codex
echo.
echo Terminals opened in: %RELATIVE_PATH%
echo.

endlocal
