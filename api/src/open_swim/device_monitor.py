import os
import time
import subprocess
from typing import Optional, Callable
import threading

OPEN_SWIM_LABEL = "OpenSwim"
MOUNT_POINT = "/mnt/openswim"

class DeviceMonitor:
    """Monitor for OpenSwim MP3 player connection/disconnection."""
    
    def __init__(self, on_connected: Callable[[str, str], None], on_disconnected: Callable[[], None]):
        """
        Initialize device monitor with callbacks.
        
        Args:
            on_connected: Callback when device connects (device_path, mount_point)
            on_disconnected: Callback when device disconnects
        """
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.connected = False
        self.current_dev: Optional[str] = None
        
    def _get_block_devices(self):
        """Returns a list of block devices like sda1, sdb1, etc."""
        devices = []
        try:
            for name in os.listdir("/dev"):
                if name.startswith("sd") and name[-1].isdigit():
                    devices.append("/dev/" + name)
            return devices
        except Exception as e:
            print(f"[ERROR] Failed to list devices: {e}")
            raise e

    def _get_label(self, dev: str) -> Optional[str]:
        """Returns filesystem label of a device or None."""
        try:
            output = subprocess.check_output(["blkid", dev]).decode()
            for part in output.split():
                if part.startswith("LABEL=") or part.startswith("LABEL_FATBOOT="):
                    return part.split("=")[1].strip('"')
        except Exception as e:
            print(f"[ERROR] Failed to get label for {dev}: {e}")
            raise e

    def _mount_device(self, dev: str) -> bool:
        """Mount the device and return success status."""
        try:
            print(f"[INFO] Mounting {dev} at {MOUNT_POINT}...")
            os.makedirs(MOUNT_POINT, exist_ok=True)
            result = subprocess.run(["mount", dev, MOUNT_POINT], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[INFO] Successfully mounted {dev}")
                return True
            else:
                print(f"[ERROR] Failed to mount: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Mount exception: {e}")
            raise e

    def _unmount_device(self) -> bool:
        """Unmount the device and return success status."""
        try:
            print(f"[INFO] Unmounting {MOUNT_POINT}...")
            result = subprocess.run(["umount", MOUNT_POINT], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("[INFO] Successfully unmounted")
                return True
            else:
                print(f"[WARN] Unmount warning: {result.stderr}")
                return True  # Don't treat this as fatal
        except Exception as e:
            print(f"[ERROR] Unmount exception: {e}")
            raise e




    def start_monitoring(self):
        """Start the monitoring loop in a background thread."""
        if hasattr(self, "_monitor_thread") and self._monitor_thread.is_alive():
            print("[INFO] Monitoring already running.")
            return
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_loop_background, daemon=True)
        self._monitor_thread.start()
        print("[INFO] Device monitoring started in background.")

    def stop_monitoring(self):
        """Stop the background monitoring loop."""
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
            if hasattr(self, "_monitor_thread"):
                self._monitor_thread.join()
            print("[INFO] Device monitoring stopped.")

    def _monitor_loop_background(self):
        """Background thread target for monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._monitor_loop()
                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Exception in monitor loop: {e}")
                time.sleep(3)

    def _monitor_loop(self):
        """Main monitoring loop (single iteration)."""
        #print(f"[INFO] Watching for {OPEN_SWIM_LABEL} device...")

        devices = self._get_block_devices()
        found_dev = None

        # Look for OpenSwim among all detected devices
        for dev in devices:
            label = self._get_label(dev)
            if label == OPEN_SWIM_LABEL:
                found_dev = dev
                break

        if found_dev and not self.connected:
            # Device plugged in
            if self._mount_device(found_dev):                
                self.connected = True
                self.current_dev = found_dev
                self.on_connected(found_dev, MOUNT_POINT)

        if self.connected and (not found_dev):
            # Device unplugged
            self._unmount_device()           
            self.connected = False
            self.current_dev = None
            self.on_disconnected()

        
