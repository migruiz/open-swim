# syntax=docker/dockerfile:1.7

FROM --platform=$TARGETPLATFORM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system packages first (least likely to change)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    util-linux \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python system packages
RUN pip install --no-cache-dir yt-dlp piper-tts

# Download Piper voice files (infrequent changes)
RUN mkdir -p /voices && \
    curl -L -o /voices/en_US-hfc_female-medium.onnx \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx?download=true" && \
    curl -L -o /voices/en_US-hfc_female-medium.onnx.json \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json?download=true"

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files and install project dependencies in editable mode
COPY pyproject.toml ./
# COPY uv.lock ./  # uncomment when lock file is added

RUN uv pip install --system --no-cache -e .

# Copy application source last (most likely to change)
COPY src ./src

# Create mount point directory
RUN mkdir -p /mnt/openswim

# Run as root to allow mounting operations
# Note: Container must be run with --privileged flag or appropriate capabilities

CMD ["open-swim"]
