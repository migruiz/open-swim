#!/bin/sh
# Keeps yt-dlp fresh on a persistent volume so YouTube extraction doesn't rot.
#
# The standalone yt-dlp binary lives at $YTDLP_DIR (a Docker volume), so updates
# survive container restarts, recreation, and image rebuilds. We download it on
# first run, update it on every start, and again every day at YTDLP_UPDATE_TIME
# (local time; mount /etc/localtime to use the host's zone) while the app runs.
# The app additionally updates and retries when a download fails
# (media/youtube/ytdlp.py). The app is pointed at it via YTDLP_PATH.
set -eu

YTDLP_DIR="${YTDLP_DIR:-/opt/ytdlp}"
YTDLP_BIN="${YTDLP_DIR}/yt-dlp"
# nightly is what yt-dlp recommends for YouTube: fixes land there days before stable.
CHANNEL="${YTDLP_UPDATE_CHANNEL:-nightly}"
UPDATE_TIME="${YTDLP_UPDATE_TIME:-00:00}"

pick_asset() {
  case "$(uname -m)" in
    aarch64|arm64)  echo "yt-dlp_linux_aarch64" ;;
    *)              echo "" ;;
  esac
}

release_repo() {
  case "$CHANNEL" in
    stable)  echo "yt-dlp/yt-dlp" ;;
    master)  echo "yt-dlp/yt-dlp-master-builds" ;;
    *)       echo "yt-dlp/yt-dlp-nightly-builds" ;;
  esac
}

download_ytdlp() {
  asset="$(pick_asset)"
  if [ -z "$asset" ]; then
    echo "[ytdlp] Unknown architecture $(uname -m); cannot fetch standalone binary" >&2
    return 1
  fi
  url="https://github.com/$(release_repo)/releases/latest/download/${asset}"
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
  echo "[ytdlp] $(date '+%F %T') Checking for update on ${CHANNEL} (current $("$YTDLP_BIN" --version 2>/dev/null || echo unknown))..."
  "$YTDLP_BIN" --update-to "$CHANNEL" 2>&1 || echo "[ytdlp] Self-update failed; keeping current version" >&2
}

seconds_until_next_update() {
  now=$(date +%s)
  next=$(date -d "today ${UPDATE_TIME}" +%s 2>/dev/null || echo 0)
  if [ "$next" -le "$now" ]; then
    next=$(date -d "tomorrow ${UPDATE_TIME}" +%s 2>/dev/null || echo $(( now + 86400 )))
  fi
  echo $(( next - now ))
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
  # Always check on start: the update is one GitHub request, and a stale
  # yt-dlp is the most common reason downloads stop working.
  self_update
fi

# Daily refresher for long-running containers.
if [ -x "$YTDLP_BIN" ]; then
  (
    while true; do
      sleep "$(seconds_until_next_update)"
      self_update
      # Step past the target minute so a fast update can't fire twice.
      sleep 61
    done
  ) &
fi

echo "[ytdlp] Using YTDLP_PATH=${YTDLP_PATH:-unset} (channel ${CHANNEL}, daily update at ${UPDATE_TIME})"
exec "$@"
