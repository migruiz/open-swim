# syntax=docker/dockerfile:1.7
##############################################
# Base builder stage (multi-arch capable)
##############################################
FROM --platform=$TARGETPLATFORM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_SYNC_PROGRESS=1 \
    VENV_PATH=/opt/venv

# Install system deps (if any needed later) and curl for uv installation
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (static binary) - https://docs.astral.sh/uv/installation/#standalone-installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy project metadata first for layer caching
COPY pyproject.toml README.md ./
# If you have a lock file later, uncomment:
# COPY uv.lock ./

# Create venv and install deps (none yet, but keeps flow consistent)
RUN uv venv $VENV_PATH \
 && . $VENV_PATH/bin/activate \
 && uv sync --no-dev --frozen || uv sync --no-dev

# Copy source after deps
COPY src ./src

# Install project into venv as a package (editable not needed inside container)
RUN . $VENV_PATH/bin/activate && uv pip install .

##############################################
# Runtime stage (slim final image)
##############################################
FROM --platform=$TARGETPLATFORM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VENV_PATH=/opt/venv
WORKDIR /app

# Copy venv from builder (contains deps + project)
COPY --from=builder $VENV_PATH $VENV_PATH
COPY --from=builder /app/src /app/src
COPY --from=builder /app/README.md /app/README.md

ENV PATH="$VENV_PATH/bin:$PATH"

# Default command runs the console script defined in pyproject
CMD ["open-swim"]
