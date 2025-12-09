# Plan: Running Open Swim as a Windows Service with NSSM

## Summary

**Yes, it's possible!** The codebase already has Windows support implemented. Use NSSM (Non-Sucking Service Manager) to wrap the application as a Windows service with zero code changes.

---

## NSSM Setup (Zero Code Changes)

NSSM (Non-Sucking Service Manager) wraps any executable as a Windows service.

### Setup Steps

1. Download `nssm.exe` from https://nssm.cc/download
2. Run these commands (as Administrator):

```powershell
# Install the service
nssm install OpenSwim "C:\path\to\venv\Scripts\python.exe" "-m" "open_swim"
nssm set OpenSwim AppDirectory "C:\repos\open-swim\api"
nssm set OpenSwim AppStdout "C:\logs\openswim.log"
nssm set OpenSwim AppStderr "C:\logs\openswim-error.log"
nssm set OpenSwim AppRestartDelay 5000

# Set environment variables
nssm set OpenSwim AppEnvironmentExtra MQTT_BROKER_URI=mqtt://your-broker:1883
nssm set OpenSwim AppEnvironmentExtra LIBRARY_PATH=C:\OpenSwimLibrary

# Start the service
nssm start OpenSwim
```

### Pros
- Ready in 30 minutes
- No code changes needed
- Auto-restart on crash
- Logging built-in

### Cons
- External executable dependency (~500KB)
- Some enterprises may block external executables

---

## Service Management Commands

```powershell
# Stop the service
nssm stop OpenSwim

# Restart the service
nssm restart OpenSwim

# Remove the service
nssm remove OpenSwim confirm

# Edit service configuration (opens GUI)
nssm edit OpenSwim
```

---

## Troubleshooting

- **View logs:** Check `C:\logs\openswim.log` and `C:\logs\openswim-error.log`
- **Service won't start:** Verify environment variables are set correctly
- **MQTT connection issues:** Ensure `MQTT_BROKER_URI` is reachable from Windows

---

## Key Files (Already Windows-Compatible)

| File | Purpose |
|------|---------|
| [app.py](src/open_swim/app.py) | Entry point - works on Windows |
| [device/windows/](src/open_swim/device/windows/) | Windows device detection (already implemented) |
| [config.py](src/open_swim/config.py) | Handles Windows paths correctly |

---

## External Dependencies Checklist

Ensure these are available on Windows PATH (or set via environment variables):

| Tool | Windows Availability | Env Var Override |
|------|---------------------|------------------|
| `yt-dlp` | [Download](https://github.com/yt-dlp/yt-dlp/releases) | `YTDLP_PATH` |
| `ffmpeg` | [Download](https://ffmpeg.org/download.html) | `FFMPEG_PATH` |
| `piper` | [Download](https://github.com/rhasspy/piper/releases) | `PIPER_CMD` |

---

## No Code Changes Required

This is a documentation-only task. The application already supports Windows - NSSM simply wraps it as a service.