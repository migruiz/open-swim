@echo off
setlocal enabledelayedexpansion

REM Simplified multi-arch build & push script.
REM Usage: build-push-arm64.bat [tag]
REM   tag - optional; defaults to latest
REM Always builds & pushes linux/amd64,linux/arm64 manifest using buildx.

set IMAGE=migruiz/open-swim
set TAG=latest
if not "%~1"=="" set TAG=%~1

set "CREDENTIALS_FILE=%~dp0dockerhub_credentials.txt"
echo [INFO] Image: %IMAGE%:%TAG%
echo [INFO] Credentials: %CREDENTIALS_FILE%

if not exist "%CREDENTIALS_FILE%" (
    echo [ERROR] Credentials file missing.
    exit /b 1
)

for /f "usebackq tokens=1,2 delims=:" %%a in ("%CREDENTIALS_FILE%") do (
    echo %%b | docker login --username %%a --password-stdin || (echo [ERROR] Login failed & exit /b 1)
    set "DOCKERHUB_USERNAME=%%a"
    goto :creds_done
)

:creds_done

echo [INFO] Ensuring buildx builder exists...
docker buildx ls | findstr /R /C:"^open-swim-builder" >nul
if errorlevel 1 (
    docker buildx create --name open-swim-builder --driver docker-container --use || (echo [ERROR] Failed to create builder & exit /b 1)
) else (
    docker buildx use open-swim-builder
)

docker buildx inspect --bootstrap >nul 2>&1

echo [INFO] Building & pushing multi-arch (amd64, arm64) image...
docker buildx build --platform linux/amd64,linux/arm64 -t %IMAGE%:%TAG% --push .
if errorlevel 1 (
    echo [ERROR] Build or push failed.
    docker logout >nul 2>&1
    exit /b 1
)

echo [INFO] Verifying manifest platforms...
for /f "delims=" %%P in ('docker buildx imagetools inspect %IMAGE%:%TAG% 2^>nul') do (
    echo %%P | findstr /I /C:"linux/amd64" >nul && set HAVE_AMD64=1
    echo %%P | findstr /I /C:"linux/arm64" >nul && set HAVE_ARM64=1
)
if not defined HAVE_AMD64 echo [WARN] linux/amd64 not found in manifest.
if not defined HAVE_ARM64 echo [WARN] linux/arm64 not found in manifest.
if defined HAVE_AMD64 if defined HAVE_ARM64 echo [INFO] Multi-arch manifest OK.

docker logout >nul 2>&1
echo [INFO] Done.
endlocal
