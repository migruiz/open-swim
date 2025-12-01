import json
import time
from typing import Any

from dotenv import load_dotenv

from open_swim.device.monitor import DeviceMonitor
from open_swim.media.podcast.episodes import update_episodes_to_sync
from open_swim.media.podcast.sync import enqueue_episode_sync
from open_swim.media.youtube.library_sync import enqueue_playlist_library_sync
from open_swim.media.youtube.playlists_to_sync import update_playlists_to_sync
from open_swim.messaging.mqtt import MqttClient


load_dotenv()


def run() -> None:
    print("Open Swim running. Hello arm64 world!")

    mqtt_client = MqttClient(
        on_connect_callback=lambda: _on_mqtt_connected(mqtt_client),
        on_message_callback=lambda topic, message: _on_mqtt_message(
            topic, message, mqtt_client
        ),
    )

    device_monitor = DeviceMonitor(
        on_connected=lambda device, mount_point: _publish_device_status(
            mqtt_client, "connected", device, mount_point
        ),
        on_disconnected=lambda: _publish_device_status(mqtt_client, "disconnected"),
    )

    device_monitor.start_monitoring()

    try:
        mqtt_client.connect_and_listen()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        mqtt_client.disconnect()
        device_monitor.stop_monitoring()


def _on_mqtt_connected(mqtt_client: MqttClient) -> None:
    mqtt_client.subscribe("openswim/episodes_to_sync")
    mqtt_client.subscribe("openswim/playlists_to_sync")
    enqueue_episode_sync()
    enqueue_playlist_library_sync()


def _on_mqtt_message(topic: str, message: Any, mqtt_client: MqttClient) -> None:
    """Handle incoming MQTT messages."""
    print(f"[MQTT] Message received on topic '{topic}': {message}")
    match topic:
        case "openswim/episodes_to_sync":
            update_episodes_to_sync(str(message))
        case "openswim/playlists_to_sync":
            update_playlists_to_sync(str(message))
        case _:
            print(f"[MQTT] Unhandled topic {topic}")


def _publish_device_status(
    mqtt_client: MqttClient, status: str, device: str | None = None, mount_point: str | None = None
) -> None:
    """Publish device status change to MQTT."""
    if mqtt_client.client is None:
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
    mqtt_client.publish(topic, payload, qos=1, retain=True)
    print(f"[MQTT] Published {status} event to {topic}")


if __name__ == "__main__":
    run()
