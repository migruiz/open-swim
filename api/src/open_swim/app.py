import json
import time
import sys
from typing import Any, Optional

from dotenv import load_dotenv

from open_swim.config import config
from open_swim.device import create_device_monitor
from open_swim.media.podcast.episodes_to_sync import update_episodes_to_sync
from open_swim.sync import enqueue_sync
from open_swim.media.youtube.playlists_to_sync import update_playlists_to_sync
from open_swim.messaging.mqtt import MqttClient


load_dotenv()

# Module-level instances for access by callbacks
_device_monitor = None
_mqtt_client: MqttClient | None = None


def get_device_monitor() -> Optional[Any]:
    """Get the device monitor instance."""
    return _device_monitor


def run() -> None:
    global _device_monitor, _mqtt_client

    config.validate_required()
    print("Open Swim running. Hello arm64 world!")

    _mqtt_client = MqttClient(
        on_connect_callback=_on_mqtt_connected,
        on_message_callback=_on_mqtt_message,
    )

    _device_monitor = create_device_monitor(
        on_connected=_on_device_connected,
        on_disconnected=_on_device_disconnected,
    )

    _device_monitor.start_monitoring()

    try:
        _mqtt_client.connect_and_listen()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        _mqtt_client.disconnect()
        _device_monitor.stop_monitoring()


def _on_mqtt_connected(client: MqttClient) -> None:
    client.subscribe("openswim/episodes_to_sync")
    client.subscribe("openswim/playlists_to_sync")
    enqueue_sync()


def _on_mqtt_message(client: MqttClient, topic: str, message: Any) -> None:
    """Handle incoming MQTT messages."""
    print(f"[MQTT] Message received on topic '{topic}': {message}")
    match topic:
        case "openswim/episodes_to_sync":
            update_episodes_to_sync(str(message))
        case "openswim/playlists_to_sync":
            update_playlists_to_sync(str(message))
        case _:
            print(f"[MQTT] Unhandled topic {topic}")


def _on_device_connected(monitor: Any, device: str, mount_point: str) -> None:
    """Handle device connected event."""
    print(f"[DEVICE] Device connected: {device} at {mount_point}")

    enqueue_sync()

    _publish_device_status(status="connected", device=device, mount_point=mount_point)


def _on_device_disconnected(monitor: Any) -> None:
    """Handle device disconnected event."""
    print("[DEVICE] Device disconnected")
    _publish_device_status(status="disconnected")


def _publish_device_status(
    status: str, device: str | None = None, mount_point: str | None = None
) -> None:
    """Publish device status change to MQTT."""
    if _mqtt_client is None or _mqtt_client.client is None:
        print("[MQTT] Skipping device status publish; client not connected yet.")
        return

    topic = "openswim/device/status"
    payload = json.dumps(
        {
            "status": status,
            "device": device,
            "mount_point": mount_point,
            "timestamp": time.time(),
        }
    )
    _mqtt_client.publish(topic, payload, qos=1, retain=True)
    print(f"[MQTT] Published {status} event to {topic}")


if __name__ == "__main__":
    run()
