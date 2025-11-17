# open-swim

Minimal Python project managed by **uv** and containerized for **arm64**.

## Prerequisites
- Python >= 3.11 (for local runs)
- `uv` installed (Windows PowerShell):
  ```powershell
  irm https://astral.sh/uv/install.ps1 | iex
  ```
- Docker with Buildx enabled for multi-arch builds.

## Install & Run Locally
```powershell
uv sync
uv run open-swim
```

## Project Structure
```
pyproject.toml
src/open_swim/__init__.py
src/open_swim/main.py
```

## Add a Dependency
```powershell
uv add requests
uv sync
```

## Container Build (arm64 only)
Build explicitly for arm64:
```powershell
docker buildx build --platform linux/arm64 -t open-swim:0.1.0 .
```
Run the container:
```powershell
docker run --rm open-swim:0.1.0
```

## Multi-Platform Image (amd64 + arm64)
```powershell
docker buildx build --platform linux/amd64,linux/arm64 -t yourrepo/open-swim:0.1.0 --push .
```
(Requires a registry login and configured builder.)

## Notes
- `uv sync` creates a `.venv` you generally do NOT copy into the image; the Dockerfile below performs a clean install inside the container.
- Adjust `requires-python` in `pyproject.toml` if you need another version.
