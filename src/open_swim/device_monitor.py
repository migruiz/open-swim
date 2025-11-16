import os
import time
import subprocess
import json
from typing import Optional
import paho.mqtt.client as mqtt

OPEN_SWIM_LABEL = "OpenSwim"
MOUNT_POINT = "/mnt/openswim"

class DeviceMonitor:
    """Monitor for OpenSwim MP3 player connection/disconnection."""
    
    def __init__(self, mqtt_client: mqtt.Client):
        self.mqtt_client = mqtt_client
        self.connected = False
        self.current_dev: Optional[str] = None
        
    def get_block_devices(self):
        """Returns a list of block devices like sda1, sdb1, etc."""
        devices = []
        try:
            for name in os.listdir("/dev"):
                if name.startswith("sd") and name[-1].isdigit():
                    devices.append("/dev/" + name)
        except Exception as e:
            print(f"[ERROR] Failed to list devices: {e}")
        return devices

    def get_label(self, dev: str) -> Optional[str]:
        """Returns filesystem label of a device or None."""
        try:
            output = subprocess.check_output(["blkid", dev]).decode()
            for part in output.split():
                if part.startswith("LABEL=") or part.startswith("LABEL_FATBOOT="):
                    return part.split("=")[1].strip('"')
        except Exception:
            return None

    def mount_device(self, dev: str) -> bool:
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
            return False

    def unmount_device(self) -> bool:
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
            return False

    def on_connected(self, device: str):
        """Handle device connection event."""
        print(f"[EVENT] OpenSwim connected at {device} and mounted at {MOUNT_POINT}")
        
        # Publish MQTT message
        topic = "openswim/device/status"
        payload = json.dumps({
            "status": "connected",
            "device": device,
            "mount_point": MOUNT_POINT,
            "timestamp": time.time()
        })
        
        result = self.mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published connection event to {topic}")

    def on_disconnected(self):
        """Handle device disconnection event."""
        print("[EVENT] OpenSwim disconnected")
        
        # Publish MQTT message
        topic = "openswim/device/status"
        payload = json.dumps({
            "status": "disconnected",
            "timestamp": time.time()
        })
        
        result = self.mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published disconnection event to {topic}")

    def monitor_loop(self):
        """Main monitoring loop."""
        print(f"[INFO] Watching for {OPEN_SWIM_LABEL} device...")

        while True:
            try:
                devices = self.get_block_devices()
                found_dev = None

                # Look for OpenSwim among all detected devices
                for dev in devices:
                    label = self.get_label(dev)
                    if label == OPEN_SWIM_LABEL:
                        found_dev = dev
                        break

                if found_dev and not self.connected:
                    # Device plugged in
                    if self.mount_device(found_dev):
                        self.on_connected(found_dev)
                        self.connected = True
                        self.current_dev = found_dev

                if self.connected and (not found_dev):
                    # Device unplugged
                    self.unmount_device()
                    self.on_disconnected()
                    self.connected = False
                    self.current_dev = None

                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n[INFO] Stopping device monitor...")
                if self.connected:
                    self.unmount_device()
                raise
            except Exception as e:
                print(f"[ERROR] Monitor loop error: {e}")
                time.sleep(5)  # Wait longer on error
