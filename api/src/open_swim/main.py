import json
import time
from open_swim.mqtt_client import MQTTClient
from open_swim.device_monitor import DeviceMonitor
from open_swim.playlist_extractor import extract_playlist
from open_swim.mp3_downloader import download_mp3
from open_swim.library_info import load_library_info, save_file_to_library, add_mp3_to_library_info
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    print("Open Swim running. Hello arm64 world!")

    # Set up MQTT connection callback

    def on_mqtt_connected() -> None:
        """Subscribe to test topic when connected. Also extract and publish playlist details."""
        print("[MQTT] Connected to broker, ready to publish/subscribe.")
        mqtt_client.subscribe("test/topic")

        # Extract playlist details and publish them
        playlist_url = "https://youtube.com/playlist?list=PLJLM5RvmYjvyPc4w6TwVB212xjar0wubX&si=9HiBeaMjWphBZ_bY"
        playlist_videos = extract_playlist(playlist_url)
        for video in playlist_videos:
            library_info = load_library_info()
            if library_info.videos.get(video.id):
                print(
                    f"[Library Info] Video ID {video.id} already in library.")
                continue
            else:
                downloaded_mp3_info = download_mp3(video_id=video.id)
                mp3_file_library_path = save_file_to_library(
                    mp3_info=downloaded_mp3_info)
                add_mp3_to_library_info(
                    library_data=library_info,
                    youtube_video=video,
                    downloaded_mp3_info=downloaded_mp3_info,
                    mp3_file_library_path=mp3_file_library_path
                )
        print(
            f"[Playlist] Extracted and processed {len(playlist_videos)} videos from playlist.")

    def on_mqtt_message(topic: str, message: str) -> None:
        """Handle incoming MQTT messages."""
        print(f"[MQTT] Message received on topic '{topic}': {message}")

    # Create MQTT client
    mqtt_client = MQTTClient(
        on_connect_callback=on_mqtt_connected,
        on_message_callback=on_mqtt_message
    )

    # Define device event handlers that publish to MQTT

    def handle_device_connected(device: str, mount_point: str) -> None:
        """Handle device connection - publish to MQTT."""
        topic = "openswim/device/status"
        payload = json.dumps({
            "status": "connected",
            "device": device,
            "mount_point": mount_point,
            "timestamp": time.time()
        })
        mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published connection event to {topic}")

    def handle_device_disconnected() -> None:
        """Handle device disconnection - publish to MQTT."""
        topic = "openswim/device/status"
        payload = json.dumps({
            "status": "disconnected",
            "timestamp": time.time()
        })
        mqtt_client.publish(topic, payload, qos=1, retain=True)
        print(f"[MQTT] Published disconnection event to {topic}")

    # Start device monitor with callbacks
    device_monitor = DeviceMonitor(
        on_connected=handle_device_connected,
        on_disconnected=handle_device_disconnected
    )

    try:
        mqtt_client.loop_forever()

    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.disconnect()
        device_monitor.stop_monitoring()
    except Exception as e:
        print(f"Error: {e}")
        mqtt_client.disconnect()
        device_monitor.stop_monitoring()


if __name__ == "__main__":
    main()
