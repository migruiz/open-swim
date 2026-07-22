#!/bin/sh
# Keeps yt-dlp fresh on a persistent volume so YouTube extraction doesn't rot.
#
# The standalone yt-dlp binary lives at $YTDLP_DIR (a Docker volume), so updates
# survive container restarts, recreation, and image rebuilds. We download it on
# run, update on start when it's older than the interval, and refresh it every
# YTDLP_UPDATE_INTERVAL_DAYS while the app runs. The app is pointed at it via
# YTDLP_PATH.
set -eu

YTDLP_DIR="${YTDLP_DIR:-/opt/ytdlp}"
YTDLP_BIN="${YTDLP_DIR}/yt-dlp"
INTERVAL_DAYS="${YTDLP_UPDATE_INTERVAL_DAYS:-7}"
INTERVAL_SECS=$(( INTERVAL_DAYS * 86400 ))

pick_asset() {
  case "$(uname -m)" in
    aarch64|arm64)  echo "yt-dlp_linux_aarch64" ;;
    x86_64|amd64)   echo "yt-dlp_linux" ;;
    armv7l|armv6l)  echo "yt-dlp_linux_armv7l" ;;
    *)              echo "" ;;
  esac
}

download_ytdlp() {
  asset="$(pick_asset)"
  if [ -z "$asset" ]; then
    echo "[ytdlp] Unknown architecture $(uname -m); cannot fetch standalone binary" >&2
    return 1
  fi
  url="https://github.com/yt-dlp/yt-dlp/releases/latest/download/${asset}"
  echo "[ytdlp] Downloading ${url}"
  tmp="${YTDLP_BIN}.tmp"
  if curl -fSL --retry 3 --retry-delay 2 -o "$tmp" "$url"; then
    chmod +x "$tmp"
    if "$tmp" --version >/dev/null 2>&1; then
      mv "$tmp" "$YTDLP_BIN"
      echo "[ytdlp] Installed yt-dlp $("$YTDLP_BIN" --version)"
      return 0
    fi
    echo "[ytdlp] Downloaded binary failed to run; discarding" >&2
    rm -f "$tmp"
  fi
  return 1
}

self_update() {
  echo "[ytdlp] Checking for update (current $("$YTDLP_BIN" --version 2>/dev/null || echo unknown))..."
  "$YTDLP_BIN" -U 2>&1 || echo "[ytdlp] Self-update failed; keeping current version" >&2
}

file_age_secs() {
  if [ -f "$1" ]; then
    echo $(( $(date +%s) - $(date -r "$1" +%s 2>/dev/null || echo 0) ))
  else
    echo 999999999
  fi
}

mkdir -p "$YTDLP_DIR"

if [ ! -x "$YTDLP_BIN" ]; then
  if download_ytdlp; then
    export YTDLP_PATH="$YTDLP_BIN"
  elif command -v yt-dlp >/dev/null 2>&1; then
    echo "[ytdlp] Falling back to bundled pip yt-dlp" >&2
    export YTDLP_PATH="$(command -v yt-dlp)"
  else
    echo "[ytdlp] WARNING: no yt-dlp available" >&2
  fi
else
  export YTDLP_PATH="$YTDLP_BIN"
  # Age-based update on start so frequently-restarted hosts still refresh every X days.
  if [ "$(file_age_secs "$YTDLP_BIN")" -ge "$INTERVAL_SECS" ]; then
    self_update
  fi
fi

# Background refresher for long-running containers.
if [ -x "$YTDLP_BIN" ]; then
  (
    while true; do
      sleep "$INTERVAL_SECS"
      self_update
    done
  ) &
fi

echo "[ytdlp] Using YTDLP_PATH=${YTDLP_PATH:-unset} (update interval: ${INTERVAL_DAYS}d)"
exec "$@"
