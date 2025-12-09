# Windows Device Monitor - Deep Dive

## Overview

The Windows device monitor detects when the OpenSwim MP3 player is plugged in or removed by polling for removable drives with a specific volume label. It uses Win32 APIs via `ctypes` to enumerate drives, check their types, and read volume labels.

## Architecture

### Initialization Flow

When the app starts (`app.py:40-47`):

```python
_device_monitor = create_device_monitor(
    on_connected=lambda device, mount_point: _on_device_connected(...),
    on_disconnected=lambda: _publish_device_status(mqtt_client, "disconnected"),
)
_device_monitor.start_monitoring()
```

The factory function `create_device_monitor()` (`device/__init__.py:24-26`) checks `sys.platform`:
- If `"win32"` → instantiates `WindowsDeviceMonitor`
- Otherwise → instantiates `LinuxDeviceMonitor`

This lazy import pattern (importing inside the if/else) ensures Windows-specific ctypes code only loads on Windows.

## WindowsDeviceMonitor Class

### State Management

The monitor maintains state (`monitor.py:42-45`):
- `self.connected` - Boolean tracking if OpenSwim is currently connected
- `self.current_dev` - The drive letter (e.g., `"E:\\"`) of the connected device
- `self._monitor_thread` - Background daemon thread
- `self._stop_event` - Threading event for graceful shutdown

### Background Thread Polling

When `start_monitoring()` is called (`monitor.py:95-105`):

1. **Creates threading.Event**: Used to signal shutdown
2. **Spawns daemon thread**: Runs `_monitor_loop_background()`
3. **Daemon=True critical**: Thread won't block app exit

The background thread loop (`monitor.py:117-123`):
```python
while not self._stop_event.is_set():
    try:
        self._monitor_loop()  # Poll once
        time.sleep(1)         # Wait 1 second
    except Exception:
        time.sleep(3)         # Longer delay on errors
```

**Why 1-second polling?** Balance between responsiveness and CPU usage. USB device detection doesn't need millisecond precision.

## Drive Detection Algorithm

Each iteration (`_monitor_loop`, lines 125-152) performs three Windows API calls:

### Step 1: Get All Removable Drives

`_list_removable_drives()` (lines 47-67):

```python
drives_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
```

**What this does:**
- `GetLogicalDrives()` returns a 32-bit integer where each bit represents a drive (A-Z)
- Bit 0 = A:, Bit 1 = B:, Bit 2 = C:, etc.
- Example: If `drives_bitmask = 0b00000000000000000000000000001100`
  - Bit 2 (C:) is set
  - Bit 3 (D:) is set
  - So C: and D: exist

Then for each bit position:
```python
for i in range(26):  # A-Z
    if drives_bitmask & (1 << i):  # Bit shifting to test each position
        drive_letter = f"{chr(65 + i)}:\\"  # 65 = ASCII 'A'
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
        if drive_type == DRIVE_REMOVABLE:  # 2 = removable media
            removable_drives.append(drive_letter)
```

**Drive Types:**
- `2` = DRIVE_REMOVABLE (USB flash drives, SD cards)
- `3` = DRIVE_FIXED (internal HDD/SSD)
- `4` = DRIVE_REMOTE (network drives)
- `5` = DRIVE_CDROM

This automatically filters to only USB/SD card drives.

### Step 2: Read Volume Labels

`_read_volume_label()` (lines 69-93):

For each removable drive, call:
```python
ctypes.windll.kernel32.GetVolumeInformationW(
    drive_letter,      # "E:\\"
    label_buffer,      # Unicode buffer to receive name
    256,               # Buffer size
    None,              # Don't need serial number
    None,              # Don't need max component length
    None,              # Don't need filesystem flags
    None,              # Don't need filesystem name
    0
)
```

**What happens:**
- Windows reads the volume label from the filesystem metadata
- The OpenSwim device has label `"OpenSwim"` set at format time
- This is stored in the FAT32 boot sector / directory entry
- Label is written into `label_buffer.value` (UTF-16 string)

### Step 3: Match and Trigger Callbacks

```python
for dev in devices:
    label = self._read_volume_label(dev)
    if label == OPEN_SWIM_LABEL:  # "OpenSwim"
        found_dev = dev
        break
```

**State machine logic:**

**Connection event** (`if found_dev and not self.connected`):
- Calls `mount_volume()` to validate
- Sets `self.connected = True`
- Stores `self.current_dev = "E:\\"`
- **Triggers callback:** `self.on_connected(device="E:\\", mount_point="E:\\")`

**Disconnection event** (`if self.connected and (not found_dev)`):
- Calls `unmount_volume()` to flush buffers
- Sets `self.connected = False`
- **Triggers callback:** `self.on_disconnected()`

**Why both conditions?** Prevents duplicate callbacks - only fires on state transitions.

## Windows Mount Functions

### mount_volume()

Located in `mount.py:5-24`:

```python
def mount_volume(drive_letter: str, mount_point: str) -> bool:
    if os.path.exists(drive_letter):
        return True
    return False
```

**Why so simple?**

Windows automatically mounts removable drives to letters. Unlike Linux where you manually run `mount /dev/sda1 /mnt/sdcard`, Windows does this instantly via Plug and Play.

The function just validates the drive letter is accessible (filesystem ready).

### unmount_volume()

Located in `mount.py:27-49`:

```python
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1)
ctypes.windll.kernel32.FlushFileBuffers(INVALID_HANDLE_VALUE)
```

**Critical for data integrity:**
- When you write files, Windows caches them in RAM
- `FlushFileBuffers(-1)` forces ALL pending writes to disk
- Without this, yanking the USB could corrupt data
- Returns non-fatal (doesn't prevent disconnection)

**Note:** This doesn't "eject" the drive (that's in `safely_eject.py` if needed). It just ensures writes complete.

### Why mount_point == drive_letter on Windows?

- **Linux:** device path (`/dev/sda1`) ≠ mount point (`/mnt/sdcard`)
- **Windows:** drive letter (`E:\\`) IS the mount point
- Rest of code uses `config.device_sd_path` which gets set to `E:\\`

## Callback Flow to App Layer

When the monitor detects connection:

1. **Monitor calls** `on_connected("E:\\", "E:\\")` (`monitor.py:144`)
2. **App receives it** in `_on_device_connected()` (`app.py:78-86`)
3. **App triggers sync** via `enqueue_sync()` (`app.py:82`)
4. **App publishes MQTT** to `"openswim/device/status"` with JSON payload

The sync worker (`sync.py:40-46`) checks:
```python
device_monitor = get_device_monitor()
if device_monitor is None or not device_monitor.connected:
    print("[SYNC] Skipping device sync: device not connected")
    return
```

This prevents syncing to a disconnected device (race condition protection).

## Key Design Decisions

### Why not use WMI or Windows Device Events?

- WMI queries are slower and more complex
- Windows provides no reliable "device arrived" event for arbitrary USB devices
- Polling is simpler, more robust, and 1-second latency is acceptable

### Why daemon thread?

- App blocks in `mqtt_client.connect_and_listen()` (`app.py:50`)
- Daemon threads die when main thread exits
- No need for explicit cleanup on shutdown

### Why flush on unmount instead of safe eject?

- Safe eject (`CreateFile` + `DeviceIoControl` with `IOCTL_STORAGE_EJECT_MEDIA`) is complex
- Users often just yank the USB
- Flushing ensures writes complete even if user doesn't eject properly
- Actual safe eject can be optional/manual

## Threading Considerations

### Race Condition Protection

- `self.connected` flag prevents double-connecting
- `self.current_dev` tracks which drive to unmount
- `if self._monitor_thread.is_alive()` prevents multiple monitor threads

### Thread Safety of Callbacks

- `on_connected()` enqueues work to a separate sync queue (`sync.py:50-52`)
- The sync queue is processed by a dedicated worker thread
- This prevents blocking the monitor thread with slow I/O

### Shutdown Sequence

```
1. KeyboardInterrupt in main thread
2. mqtt_client.disconnect() (app.py:56)
3. _device_monitor.stop_monitoring() (app.py:57)
4. Sets _stop_event (monitor.py:110)
5. Background thread sees event, exits loop (monitor.py:117)
6. Thread.join() waits for clean exit (monitor.py:112)
```

## Typical Session Flow

### Startup (no device connected)

```
[INFO] Device monitoring started in background.
[Loop iteration 1] _list_removable_drives() → []
[Loop iteration 2] _list_removable_drives() → []
... (every second)
```

### User plugs in OpenSwim

```
[Loop iteration N] _list_removable_drives() → ["E:\\"]
[Loop iteration N] _read_volume_label("E:\\") → "OpenSwim"
[Loop iteration N] found_dev = "E:\\", self.connected = False → CONNECT!
[INFO] Windows drive E:\ is available
[DEVICE] Device connected: E:\ at E:\
[SYNC] Enqueued sync work
[MQTT] Published connected event
```

### Sync runs, copies files...

### User removes USB

```
[Loop iteration M] _list_removable_drives() → [] (E: disappeared)
[Loop iteration M] self.connected = True, found_dev = None → DISCONNECT!
[INFO] Flushed file buffers for E:\
[MQTT] Published disconnected event
```

## Platform Abstraction

The beauty of this design:
- `app.py` doesn't know if it's Windows or Linux
- Both monitors implement identical interface (duck typing)
- Callbacks have same signature: `(device: str, mount_point: str)`
- Sync code uses `config.device_sd_path` which works on both:
  - Windows: `"E:\\"`
  - Linux: `"/mnt/openswim"`

The factory pattern in `device/__init__.py` is the **only** place that knows about platform differences.

## Win32 API Reference

### GetLogicalDrives()

```c
DWORD GetLogicalDrives();
```

Returns a bitmask representing available logical drives. Bit 0 = A:, Bit 1 = B:, etc.

### GetDriveTypeW()

```c
UINT GetDriveTypeW(LPCWSTR lpRootPathName);
```

Determines whether a disk drive is removable, fixed, CD-ROM, RAM disk, or network drive.

**Return values:**
- 0 = DRIVE_UNKNOWN
- 1 = DRIVE_NO_ROOT_DIR
- 2 = DRIVE_REMOVABLE
- 3 = DRIVE_FIXED
- 4 = DRIVE_REMOTE
- 5 = DRIVE_CDROM
- 6 = DRIVE_RAMDISK

### GetVolumeInformationW()

```c
BOOL GetVolumeInformationW(
  LPCWSTR lpRootPathName,
  LPWSTR  lpVolumeNameBuffer,
  DWORD   nVolumeNameSize,
  LPDWORD lpVolumeSerialNumber,
  LPDWORD lpMaximumComponentLength,
  LPDWORD lpFileSystemFlags,
  LPWSTR  lpFileSystemNameBuffer,
  DWORD   nFileSystemNameSize
);
```

Retrieves information about the file system and volume associated with the specified root directory.

### FlushFileBuffers()

```c
BOOL FlushFileBuffers(HANDLE hFile);
```

Flushes the buffers of a specified file and causes all buffered data to be written to a file. When called with `INVALID_HANDLE_VALUE (-1)`, it flushes all file system buffers.

## Implementation Notes

This implementation is elegant, robust, and follows Windows best practices for USB device detection without requiring complex COM/WMI infrastructure. The 1-second polling is perfectly acceptable for this use case where sub-second detection isn't critical.

The use of `ctypes` to call Win32 APIs directly avoids dependencies on third-party libraries like `pywin32` or `wmi`, keeping the implementation lightweight and portable.
