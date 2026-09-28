import json
import threading
import time
import sys
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from open_swim.config import config
from open_swim.device import create_device_monitor
from open_swim.media.podcast.episodes_to_sync import update_episodes_to_sync
from open_swim.media.podcast import store as podcast_store
from open_swim.sync import enqueue_sync, enqueue_sync_after_quiet_period, start_periodic_sync
from open_swim.media.youtube.playlists_to_sync import update_playlists_to_sync
from open_swim.media.youtube.playlists import fetch_playlist_information
from open_swim.messaging.models import (
    PlaylistInfoRequest,
    PlaylistInfoResponse,
    PlaylistInfoVideoItem,
)
from open_swim.messaging.mqtt import MqttClient
from open_swim.messaging.progress import MqttProgressReporter, set_progress_reporter


# Module-level instances for access by callbacks
_device_monitor = None
_mqtt_client: MqttClient | None = None
# Last player status, republished on every MQTT (re)connect.
_last_device_status: tuple[str, str | None, str | None] = ("disconnected", None, None)


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
    set_progress_reporter(MqttProgressReporter(_mqtt_client))

    _device_monitor = create_device_monitor(
        on_connected=_on_device_connected,
        on_disconnected=_on_device_disconnected,
    )

    _device_monitor.start_monitoring()
    start_periodic_sync()

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
    client.subscribe("openswim/playlist-info/request")
    client.subscribe("openswim/episodes-to-sync/request")
    client.subscribe("openswim/playlists-to-sync/request")
    # The retained status may be stale (e.g. left by another machine that ran
    # open-swim), or a change may have happened while disconnected; replace it
    # with this instance's current view.
    status, device, mount_point = _last_device_status
    _publish_device_status(status=status, device=device, mount_point=mount_point)
    enqueue_sync()


def _on_mqtt_message(client: MqttClient, topic: str, message: Any) -> None:
    """Handle incoming MQTT messages."""
    print(f"[MQTT] Message received on topic '{topic}': {message}")
    match topic:
        case "openswim/episodes_to_sync":
            update_episodes_to_sync(str(message))
            enqueue_sync_after_quiet_period()
        case "openswim/playlists_to_sync":
            update_playlists_to_sync(str(message))
            enqueue_sync_after_quiet_period()
        case "openswim/playlist-info/request":
            _handle_playlist_info_request(client=client, message=str(message))
        case "openswim/episodes-to-sync/request":
            _handle_episodes_to_sync_request(client=client)
        case "openswim/playlists-to-sync/request":
            _handle_playlists_to_sync_request(client=client)
        case _:
            print(f"[MQTT] Unhandled topic {topic}")


def _playlist_id_from_input(value: str) -> str:
    raw = value.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        query = parse_qs(parsed.query)
        if "list" in query and query["list"]:
            return query["list"][0]
        return raw
    return raw


def _playlist_url_from_input(value: str) -> str:
    raw = value.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://youtube.com/playlist?list={raw}"


def _handle_episodes_to_sync_request(client: MqttClient) -> None:
    """Handle request for current episodes to sync list."""
    try:
        episodes = podcast_store.load_episode_requests()
        response = json.dumps([ep.model_dump(mode="json") for ep in episodes])
        client.publish(
            "openswim/episodes-to-sync/response",
            response,
            qos=1,
            retain=False,
        )
        print(f"[MQTT] Published episodes-to-sync response with {len(episodes)} episodes")
    except Exception as exc:
        print(f"[MQTT] Failed to handle episodes-to-sync request: {exc}")


def _handle_playlists_to_sync_request(client: MqttClient) -> None:
    """Handle request for current playlists to sync list."""
    try:
        from open_swim.media.youtube import store as youtube_store
        playlists = youtube_store.load_playlist_requests()
        response = json.dumps([pl.model_dump(mode="json") for pl in playlists])
        client.publish(
            "openswim/playlists-to-sync/response",
            response,
            qos=1,
            retain=False,
        )
        print(f"[MQTT] Published playlists-to-sync response with {len(playlists)} playlists")
    except Exception as exc:
        print(f"[MQTT] Failed to handle playlists-to-sync request: {exc}")


def _handle_playlist_info_request(client: MqttClient, message: str) -> None:
    def _work() -> None:
        playlist_id: str | None = None
        try:
            payload = json.loads(message)
            request = PlaylistInfoRequest(**payload)
            playlist_id = _playlist_id_from_input(request.playlist_id)
            playlist_url = _playlist_url_from_input(request.playlist_id)

            info = fetch_playlist_information(
                playlist_url=playlist_url,
                playlist_title=playlist_id or "playlist",
            )
            response = PlaylistInfoResponse(
                success=True,
                playlist_id=info.id,
                title=info.title,
                videos=[
                    PlaylistInfoVideoItem(id=video.id, title=video.title)
                    for video in info.videos
                ],
            )
        except Exception as exc:
            response = PlaylistInfoResponse(
                success=False,
                playlist_id=playlist_id,
                error=str(exc),
            )

        try:
            client.publish(
                "openswim/playlist-info/response",
                response.model_dump_json(),
                qos=1,
                retain=False,
            )
        except Exception as exc:  # pragma: no cover - best effort only
            print(f"[MQTT] Failed to publish playlist info response: {exc}")

    threading.Thread(target=_work, daemon=True).start()


def _on_device_connected(monitor: Any, device: str, mount_point: str) -> None:
    """Handle device connected event."""
    print(f"[DEVICE] Device connected: {device} at {mount_point}")

    enqueue_sync()

    _publish_device_status(status="connected", device=device, mount_point=mount_point)


def release_device() -> None:
    """Flush and unmount the device after a copy, then announce it is safe to unplug."""
    if _device_monitor is None:
        return
    if _device_monitor.release():
        print("[DEVICE] Device released; safe to unplug")
        _publish_device_status(
            status="safe_to_unplug", device=_device_monitor.current_dev
        )
    else:
        print("[DEVICE] Device not released after sync")


def _on_device_disconnected(monitor: Any) -> None:
    """Handle device disconnected event."""
    print("[DEVICE] Device disconnected")
    _publish_device_status(status="disconnected")


def _publish_device_status(
    status: str, device: str | None = None, mount_point: str | None = None
) -> None:
    """Publish device status change to MQTT."""
    global _last_device_status
    _last_device_status = (status, device, mount_point)
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
