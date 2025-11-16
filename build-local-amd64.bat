@echo off
setlocal enabledelayedexpansion

REM Build and run the image locally for linux/amd64
set IMAGE=migruiz/open-swim
set TAG=local-amd64

echo === Building %IMAGE%:%TAG% for linux/amd64 ===
docker build --platform=linux/amd64 -t %IMAGE%:%TAG% .
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo === Running container ===
docker run --rm --name open-swim %IMAGE%:%TAG%

endlocal
