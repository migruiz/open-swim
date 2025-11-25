import json
import time
from open_swim.mqtt_client import MQTTClient, MQTTCallbacks
from open_swim.device_monitor import DeviceMonitor


def main() -> None:
    print("Open Swim running. Hello arm64 world!")
    
    # Create MQTT callbacks
    mqtt_callbacks = MQTTCallbacks()
    
    # Set up MQTT connection callback
    def on_connect(client, userdata, flags, rc, properties=None):
        """Subscribe to test topic when connected."""
        test_topic = "test/topic"
        client.subscribe(test_topic)
        print(f"Subscribed to topic: {test_topic}")
    
    mqtt_callbacks.set_on_connect(on_connect)
    
    # Create MQTT client
    mqtt_client = MQTTClient(mqtt_callbacks)
    
    try:
        # Connect to broker
        mqtt_client.connect()
        
        # Publish a test message
        test_topic = "test/topic"
        test_message = "Hello from Open Swim!"
        mqtt_client.publish(test_topic, test_message)
        print(f"Publishing message to topic '{test_topic}': {test_message}")
        
        # Define device event handlers that publish to MQTT
        def handle_device_connected(device: str, mount_point: str):
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
        
        def handle_device_disconnected():
            """Handle device disconnection - publish to MQTT."""
            topic = "openswim/device/status"
            payload = json.dumps({
                "status": "disconnected",
                "timestamp": time.time()
            })
            mqtt_client.publish(topic, payload, qos=1, retain=True)
            print(f"[MQTT] Published disconnection event to {topic}")
        
        # Start device monitor with callbacks
        monitor = DeviceMonitor(
            on_connected=handle_device_connected,
            on_disconnected=handle_device_disconnected
        )
        print("[INFO] Starting OpenSwim device monitor...")
        monitor.monitor_loop()
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
