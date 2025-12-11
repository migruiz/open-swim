@echo off
setlocal enabledelayedexpansion

:: Launch Parallel Development - .bat version
:: Usage: feature-parallel.bat [plan-file-path]
:: If no argument, auto-detects latest .md file in ~/.claude/plans/

:: Handle argument - plan file path or auto-detect
if "%~1"=="" (
    :: No argument - find latest .md file in plans folder
    echo No plan file specified, auto-detecting latest plan...
    for /f "delims=" %%i in ('powershell -Command "Get-ChildItem '%USERPROFILE%\.claude\plans\*.md' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"') do set "PLAN_FILE=%%i"
    if "!PLAN_FILE!"=="" (
        echo Error: No plan files found in %USERPROFILE%\.claude\plans\
        echo Run /plan-feature first to create a plan.
        exit /b 1
    )
    echo Auto-detected: !PLAN_FILE!
) else (
    set "PLAN_FILE=%~1"
)

:: Validate plan file exists
if not exist "%PLAN_FILE%" (
    echo Error: Plan file not found: %PLAN_FILE%
    exit /b 1
)

:: Parse plan file using PowerShell - extract FEATURE_NAME
echo Parsing plan file...
for /f "delims=" %%i in ('powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; $m = [regex]::Match($c, '<!-- FEATURE_NAME: (.+?) -->'); if ($m.Success) { $m.Groups[1].Value.Trim() } else { '' }"') do set "FEATURE=%%i"

if "%FEATURE%"=="" (
    echo Error: Could not extract FEATURE_NAME from plan file
    echo Make sure the plan file contains: ^<^!-- FEATURE_NAME: your-feature-name --^>
    exit /b 1
)

:: Validate BRIEF section exists
powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; if ($c -notmatch '<!-- BEGIN_BRIEF -->') { exit 1 }"
if errorlevel 1 (
    echo Error: BEGIN_BRIEF marker not found in plan file
    exit /b 1
)
powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; if ($c -notmatch '<!-- END_BRIEF -->') { exit 1 }"
if errorlevel 1 (
    echo Error: END_BRIEF marker not found in plan file
    exit /b 1
)

:: Validate PLAN section exists
powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; if ($c -notmatch '<!-- BEGIN_PLAN -->') { exit 1 }"
if errorlevel 1 (
    echo Error: BEGIN_PLAN marker not found in plan file
    exit /b 1
)
powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; if ($c -notmatch '<!-- END_PLAN -->') { exit 1 }"
if errorlevel 1 (
    echo Error: END_PLAN marker not found in plan file
    exit /b 1
)

echo Found feature: %FEATURE%

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

echo.
echo === Launch Parallel Development ===
echo Feature: %FEATURE%
echo Repo: %REPO_NAME%
echo Relative path: %RELATIVE_PATH%
echo Plan file: %PLAN_FILE%
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

:: Step 3: Extract and write plan files from parsed content
echo [3/7] Extracting plan files...
powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; $brief = [regex]::Match($c, '(?s)<!-- BEGIN_BRIEF -->(.+?)<!-- END_BRIEF -->').Groups[1].Value.Trim(); Set-Content -Path 'plans\%FEATURE%\brief.md' -Value $brief -Encoding UTF8 -NoNewline"
if errorlevel 1 (
    echo Error: Failed to extract brief.md
    exit /b 1
)
echo   - Created brief.md

powershell -Command "$c = Get-Content '%PLAN_FILE%' -Raw; $plan = [regex]::Match($c, '(?s)<!-- BEGIN_PLAN -->(.+?)<!-- END_PLAN -->').Groups[1].Value.Trim(); Set-Content -Path 'plans\%FEATURE%\plan.md' -Value $plan -Encoding UTF8 -NoNewline"
if errorlevel 1 (
    echo Error: Failed to extract plan.md
    exit /b 1
)
echo   - Created plan.md

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
set "CLAUDE_PROMPT=You are implementing feature '%FEATURE%'. Read @plans/%FEATURE%/brief.md for context, requirements and rationale. Read @plans/%FEATURE%/plan.md for implementation steps. CRITICAL: Before writing ANY code, you MUST validate the plan: (1) Read both files completely (2) Verify all files referenced in the plan exist (3) Check the approach aligns with existing code patterns (4) Identify any issues, missing deps, or unclear requirements (5) Report validation findings and WAIT for confirmation. Do NOT implement until validation passes. If you find problems, explain them clearly. After validation approval, follow plan.md steps precisely. When implementation is complete, commit all your changes with a descriptive commit message."

set "CODEX_PROMPT=You are implementing feature '%FEATURE%'. Read @plans/%FEATURE%/brief.md for context and rationale. Read @plans/%FEATURE%/plan.md for implementation steps. BEFORE CODING: Validate the plan first - (1) Read both files (2) Check referenced files exist (3) Verify approach matches codebase patterns (4) Report any issues found (5) Wait for confirmation before implementing. Only proceed after validation passes. Follow plan.md steps precisely. When implementation is complete, commit all your changes with a descriptive commit message."

:: Write prompts to temp files to avoid escaping issues
set "CLAUDE_PROMPT_FILE=%TEMP%\claude_prompt_%FEATURE%.txt"
set "CODEX_PROMPT_FILE=%TEMP%\codex_prompt_%FEATURE%.txt"

echo %CLAUDE_PROMPT%> "%CLAUDE_PROMPT_FILE%"
echo %CODEX_PROMPT%> "%CODEX_PROMPT_FILE%"

:: Launch terminals - read prompt from file using Get-Content
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', \"cd '%CLAUDE_PATH%'; `$host.UI.RawUI.WindowTitle = '%FEATURE%-claude'; claude --dangerously-skip-permissions (Get-Content '%CLAUDE_PROMPT_FILE%' -Raw)\""
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', \"cd '%CODEX_PATH%'; `$host.UI.RawUI.WindowTitle = '%FEATURE%-codex'; codex --ask-for-approval never (Get-Content '%CODEX_PROMPT_FILE%' -Raw)\""

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
