# syntax=docker/dockerfile:1.7

# --- STAGE 1: Asset Downloader ---
# We use a tiny Alpine image just to download the large voice files.
# If your code changes, Docker caches this stage so you don't download 
# these 100MB+ files every time you build.
FROM alpine:latest AS assets

WORKDIR /voices
RUN apk add --no-cache curl

# Download Piper voice files
RUN curl -L -O "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx?download=true" && \
    curl -L -O "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json?download=true"


# --- STAGE 2: Python Builder (uv) ---
FROM --platform=linux/arm64 python:3.12-slim AS builder

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Create a virtual environment
# We install EVERYTHING here (deps + your app) so it's all in one folder to copy
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
ENV UV_COMPILE_BYTECODE=1

# 1. Install specific manual requirements
# We install yt-dlp and piper-tts into the venv
RUN uv venv && \
    uv pip install yt-dlp piper-tts

# 2. Install your project dependencies
# We copy only the files needed for dependency resolution first
COPY pyproject.toml ./
# COPY uv.lock ./ 

# Install dependencies (but not the project root yet) to leverage caching
RUN uv pip install -r pyproject.toml

# 3. Install your actual application
COPY src ./src
# This installs your 'src' package and creates the 'open-swim' binary in .venv/bin
RUN uv pip install .


# --- STAGE 3: Runtime (Final) ---
# arm64 only - this image targets the Raspberry Pi.
FROM --platform=linux/arm64 python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Add the venv to PATH so we can run 'open-swim' directly
    PATH="/app/.venv/bin:$PATH" \
    # yt-dlp lives on a persistent volume and self-updates on start and daily
    # (see docker-entrypoint.sh), and after a failed download (media/youtube/ytdlp.py).
    YTDLP_DIR="/opt/ytdlp" \
    YTDLP_PATH="/opt/ytdlp/yt-dlp" \
    YTDLP_UPDATE_CHANNEL="nightly" \
    YTDLP_UPDATE_TIME="00:00"

WORKDIR /app

# 1. Install Runtime System Dependencies
# We only need the libraries to RUN the app, not build it.
# curl + ca-certificates are needed to fetch/refresh the standalone yt-dlp binary.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    util-linux \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 1b. JavaScript runtime for yt-dlp
# Recent yt-dlp needs a JS runtime to extract YouTube formats; without one it
# warns "No supported JavaScript runtime could be found" and 403s on some
# videos. deno is yt-dlp's default, so no extra flags are needed.
ARG DENO_VERSION=2.9.4
RUN curl -fSL --retry 3 --retry-delay 2 -o /tmp/deno.zip \
      "https://github.com/denoland/deno/releases/download/v${DENO_VERSION}/deno-aarch64-unknown-linux-gnu.zip" && \
    unzip -q /tmp/deno.zip -d /usr/local/bin && \
    rm /tmp/deno.zip && \
    deno --version

# Directory for the persistent yt-dlp binary (mount a volume here).
RUN mkdir -p /opt/ytdlp

# 2. Copy the Voice Assets from Stage 1
COPY --from=assets /voices /voices

# 3. Copy the Virtual Environment from Stage 2
# This contains Python, yt-dlp, piper-tts, AND your open-swim app
COPY --from=builder /app/.venv /app/.venv

# 4. Create mount point
RUN mkdir -p /mnt/openswim

# 5. Entrypoint keeps yt-dlp fresh on the volume, then launches the app.
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Note: Container must be run with --privileged flag for mounting
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["open-swim"]