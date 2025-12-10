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

:: Get most recent plan file from ~/.claude/plans/
for /f "delims=" %%i in ('powershell -Command "Get-ChildItem -Path ~\.claude\plans -Filter *.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"') do set "PLAN_FILE=%%i"

echo.
echo === Launch Parallel Development (Quick) ===
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

:: Step 3: Copy plan file
echo [3/7] Copying plan file...
if exist "%PLAN_FILE%" (
    copy "%PLAN_FILE%" "plans\%FEATURE%\plan.md" >nul
) else (
    echo Warning: No plan file found in ~/.claude/plans/
)

:: Step 4: Commit
echo [4/7] Committing plan...
git add "plans\%FEATURE%\"
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

:: Step 7: Open terminals
echo [7/7] Opening terminals...
set "CLAUDE_PATH=%WORKTREES_DIR%\%FEATURE%-claude\%RELATIVE_PATH%"
set "CODEX_PATH=%WORKTREES_DIR%\%FEATURE%-codex\%RELATIVE_PATH%"

start "claude" powershell -NoExit -Command "$host.UI.RawUI.WindowTitle = '%FEATURE%-claude'; cd '%CLAUDE_PATH%'; claude"
start "codex" powershell -NoExit -Command "$host.UI.RawUI.WindowTitle = '%FEATURE%-codex'; cd '%CODEX_PATH%'; codex"

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
