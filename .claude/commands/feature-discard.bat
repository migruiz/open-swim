@echo off
setlocal enabledelayedexpansion

:: Feature Discard - Cleanup feature branches and worktrees
:: Usage: feature-discard.bat feature-name

:: Validate argument
if "%~1"=="" (
    echo Usage: feature-discard.bat feature-name
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

:: Set worktrees directory
set "WORKTREES_DIR=%REPO_ROOT%\..\%REPO_NAME%-worktrees"

:: Save current branch
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURRENT_BRANCH=%%i"

echo.
echo === Feature Discard ===
echo Feature: %FEATURE%
echo Repo: %REPO_NAME%
echo Current branch: %CURRENT_BRANCH%
echo.

:: Check if we're on a feature branch that will be deleted
set "ON_FEATURE_BRANCH=0"
if "%CURRENT_BRANCH%"=="features/%FEATURE%/base" set "ON_FEATURE_BRANCH=1"
if "%CURRENT_BRANCH%"=="features/%FEATURE%/claude" set "ON_FEATURE_BRANCH=1"
if "%CURRENT_BRANCH%"=="features/%FEATURE%/codex" set "ON_FEATURE_BRANCH=1"

:: If on feature branch, switch to main/master first
if "%ON_FEATURE_BRANCH%"=="1" (
    echo Switching away from feature branch...
    git checkout main 2>nul || git checkout master 2>nul
    if errorlevel 1 (
        echo Error: Could not switch to main or master branch
        exit /b 1
    )
    :: Update saved branch to main/master since original will be deleted
    for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURRENT_BRANCH=%%i"
)

:: Step 1: Remove worktrees
echo [1/3] Removing worktrees...
set "CLAUDE_WORKTREE=%WORKTREES_DIR%\%FEATURE%-claude"
set "CODEX_WORKTREE=%WORKTREES_DIR%\%FEATURE%-codex"

if exist "%CLAUDE_WORKTREE%" (
    git worktree remove "%CLAUDE_WORKTREE%" 2>nul
    if errorlevel 1 (
        echo Warning: Could not remove %FEATURE%-claude worktree. Terminal may still be open.
        git worktree remove --force "%CLAUDE_WORKTREE%" 2>nul
    )
) else (
    echo   %FEATURE%-claude worktree not found, skipping
)

if exist "%CODEX_WORKTREE%" (
    git worktree remove "%CODEX_WORKTREE%" 2>nul
    if errorlevel 1 (
        echo Warning: Could not remove %FEATURE%-codex worktree. Terminal may still be open.
        git worktree remove --force "%CODEX_WORKTREE%" 2>nul
    )
) else (
    echo   %FEATURE%-codex worktree not found, skipping
)

:: Step 2: Delete branches
echo [2/3] Deleting branches...
git branch -D "features/%FEATURE%/base" 2>nul
if errorlevel 1 echo   features/%FEATURE%/base not found, skipping
git branch -D "features/%FEATURE%/claude" 2>nul
if errorlevel 1 echo   features/%FEATURE%/claude not found, skipping
git branch -D "features/%FEATURE%/codex" 2>nul
if errorlevel 1 echo   features/%FEATURE%/codex not found, skipping

:: Step 3: Return to previous branch
echo [3/3] Returning to previous branch...
git checkout "%CURRENT_BRANCH%" 2>nul
if errorlevel 1 (
    echo Warning: Could not return to %CURRENT_BRANCH%, staying on current branch
)

echo.
echo === DONE ===
echo Feature '%FEATURE%' has been discarded.
echo Note: plans/%FEATURE%/ folder was kept.
echo.

endlocal
