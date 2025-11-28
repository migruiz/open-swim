# syntax=docker/dockerfile:1.7

# Stage 1: Build dependencies
FROM --platform=$TARGETPLATFORM python:3.12-slim AS build
WORKDIR /app

# Install uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first for better layer caching
COPY pyproject.toml README.md ./
# COPY uv.lock ./  # uncomment when lock file is added

# Install dependencies directly into system Python (no venv)
RUN uv pip install --system --no-cache .

# Copy application source
COPY src ./src

# Install the project package
RUN uv pip install --system --no-cache --no-deps .


# Stage 2: Runtime image
FROM --platform=$TARGETPLATFORM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from system site-packages
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/open-swim /usr/local/bin/open-swim

# Copy application source and metadata
COPY --from=build /app/src /app/src
COPY --from=build /app/README.md /app/README.md

# Install required system utilities for device management
RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir yt-dlp piper-tts onnxruntime

# Create mount point directory
RUN mkdir -p /mnt/openswim

# Run as root to allow mounting operations
# Note: Container must be run with --privileged flag or appropriate capabilities

CMD ["open-swim"]
