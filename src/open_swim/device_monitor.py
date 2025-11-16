import os
import time
import subprocess
import json
from typing import Optional
import paho.mqtt.client as mqtt
import pyudev

OPEN_SWIM_LABEL = "OpenSwim"
MOUNT_POINT = "/mnt/openswim"

class DeviceMonitor:
    """Monitor for OpenSwim MP3 player connection/disconnection."""
    
    def __init__(self, mqtt_client: mqtt.Client):
        self.mqtt_client = mqtt_client
        self.connected = False
        self.current_dev: Optional[str] = None
        self.context = pyudev.Context()

    def get_label(self, dev: str) -> Optional[str]:
        """Returns filesystem label of a device or None."""
        try:
            output = subprocess.check_output(["blkid", dev], stderr=subprocess.DEVNULL).decode()
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
        
        self.mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published connection event to {topic}")

    def on_disconnected(self):
        """Handle device disconnection event."""
        print("[EVENT] OpenSwim disconnected")
        
        topic = "openswim/device/status"
        payload = json.dumps({
            "status": "disconnected",
            "timestamp": time.time()
        })
        
        self.mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published disconnection event to {topic}")

    def check_existing_devices(self):
        """Check for already connected OpenSwim devices on startup."""
        print("[INFO] Checking for existing devices...")
        for device in self.context.list_devices(subsystem='block', DEVTYPE='partition'):
            label = self.get_label(device.device_node)
            if label == OPEN_SWIM_LABEL:
                print(f"[INFO] Found existing OpenSwim device: {device.device_node}")
                if self.mount_device(device.device_node):
                    self.on_connected(device.device_node)
                    self.connected = True
                    self.current_dev = device.device_node
                return

    def monitor_loop(self):
        """Main monitoring loop using udev events."""
        print(f"[INFO] Watching for {OPEN_SWIM_LABEL} device...")
        
        # Check for devices already connected
        self.check_existing_devices()
        
        # Set up udev monitor for new connections
        monitor = pyudev.Monitor.from_netlink(self.context)
        monitor.filter_by(subsystem='block', device_type='partition')
        
        try:
            for device in iter(monitor.poll, None):
                if device.action == 'add':
                    # Wait a moment for device to be ready
                    time.sleep(0.5)
                    label = self.get_label(device.device_node)
                    
                    if label == OPEN_SWIM_LABEL and not self.connected:
                        print(f"[INFO] Detected new device: {device.device_node}")
                        if self.mount_device(device.device_node):
                            self.on_connected(device.device_node)
                            self.connected = True
                            self.current_dev = device.device_node
                
                elif device.action == 'remove':
                    if self.connected and device.device_node == self.current_dev:
                        self.unmount_device()
                        self.on_disconnected()
                        self.connected = False
                        self.current_dev = None
                        
        except KeyboardInterrupt:
            print("\n[INFO] Stopping device monitor...")
            if self.connected:
                self.unmount_device()
            raise
        except Exception as e:
            print(f"[ERROR] Monitor loop error: {e}")
            time.sleep(5)
