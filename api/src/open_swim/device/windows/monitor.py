import ctypes
from ctypes import wintypes
import threading
import time
from typing import Any, Optional, Protocol

from open_swim.config import config
from open_swim.device.windows.mount import mount_volume, unmount_volume

OPEN_SWIM_LABEL = "OpenSwim"


class DeviceConnectedCallback(Protocol):
    """Protocol for device connected callback."""

    def __call__(self, monitor: Any, device: str, mount_point: str) -> None:
        ...


class DeviceDisconnectedCallback(Protocol):
    """Protocol for device disconnected callback."""

    def __call__(self, monitor: Any) -> None:
        ...


class WindowsDeviceMonitor:
    """Monitor for OpenSwim MP3 player connection/disconnection on Windows."""

    def __init__(
        self, on_connected: DeviceConnectedCallback, on_disconnected: DeviceDisconnectedCallback
    ):
        """
        Initialize device monitor with callbacks.

        Args:
            on_connected: Callback when device connects (drive_letter, mount_point)
            on_disconnected: Callback when device disconnects
        """
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.connected = False
        self.current_dev: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None

    def _list_removable_drives(self) -> list[str]:
        """Returns a list of removable drive letters like E:\\, F:\\, etc."""
        removable_drives: list[str] = []

        # Get bitmask of all logical drives
        drives_bitmask = ctypes.windll.kernel32.GetLogicalDrives()

        # Check each possible drive letter (A-Z)
        for i in range(26):
            if drives_bitmask & (1 << i):
                # Convert bit position to drive letter
                drive_letter = f"{chr(65 + i)}:\\"

                # Check if this is a removable drive
                DRIVE_REMOVABLE = 2
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)

                if drive_type == DRIVE_REMOVABLE:
                    removable_drives.append(drive_letter)

        return removable_drives

    def _read_volume_label(self, drive_letter: str) -> Optional[str]:
        """Returns filesystem label of a drive or None."""
        try:
            # Create buffer to receive the volume label
            label_buffer = ctypes.create_unicode_buffer(256)

            # Call GetVolumeInformationW
            result = ctypes.windll.kernel32.GetVolumeInformationW(
                drive_letter,     # Root path (e.g., "E:\\")
                label_buffer,     # Buffer for volume name
                256,              # Size of volume name buffer
                None,             # Volume serial number (not needed)
                None,             # Maximum component length (not needed)
                None,             # File system flags (not needed)
                None,             # File system name buffer (not needed)
                0                 # Size of file system name buffer
            )

            if result:
                return label_buffer.value
            else:
                return None
        except Exception as e:
            print(f"[ERROR] Failed to get label for {drive_letter}: {e}")
            return None

    def start_monitoring(self) -> None:
        """Start the monitoring loop in a background thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            print("[INFO] Monitoring already running.")
            return
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop_background, daemon=True
        )
        self._monitor_thread.start()
        print("[INFO] Device monitoring started in background.")

    def stop_monitoring(self) -> None:
        """Stop the background monitoring loop."""
        if self._stop_event is not None:
            self._stop_event.set()
            if self._monitor_thread is not None:
                self._monitor_thread.join()
            print("[INFO] Device monitoring stopped.")

    def _monitor_loop_background(self) -> None:
        """Background thread target for monitoring loop."""
        while self._stop_event is not None and not self._stop_event.is_set():
            try:
                self._monitor_loop()
                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Exception in monitor loop: {e}")
                time.sleep(3)

    def _monitor_loop(self) -> None:
        """Main monitoring loop (single iteration)."""
        devices = self._list_removable_drives()
        found_dev = None

        # Look for OpenSwim among all detected devices
        for dev in devices:
            label = self._read_volume_label(dev)
            if label == OPEN_SWIM_LABEL:
                found_dev = dev
                break

        if found_dev and not self.connected:
            # Device plugged in
            # On Windows, the drive letter IS the mount point
            mount_point = found_dev
            if mount_volume(found_dev, mount_point):
                self.connected = True
                self.current_dev = found_dev
                self.on_connected(self, device=found_dev, mount_point=mount_point)

        if self.connected and (not found_dev):
            # Device unplugged
            if self.current_dev:
                unmount_volume(self.current_dev)
            self.connected = False
            self.current_dev = None
            self.on_disconnected(self)
