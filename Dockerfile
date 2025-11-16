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

# Sync dependencies into .venv (creates virtual environment)
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy application source
COPY src ./src

# Install the project package into the venv
RUN uv pip install --no-deps .

# Stage 2: Runtime image (same base = compatible venv)
FROM --platform=$TARGETPLATFORM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Copy virtual environment from build stage
COPY --from=build /app/.venv /opt/venv

# Copy application source and metadata
COPY --from=build /app/src /app/src
COPY --from=build /app/README.md /app/README.md

# Fix shebang in console scripts to point to relocated venv
RUN sed -i 's|#!/app/.venv/bin/python|#!/opt/venv/bin/python|g' /opt/venv/bin/*

# Drop privileges (security best practice)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["open-swim"]
