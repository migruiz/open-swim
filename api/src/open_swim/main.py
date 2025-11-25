import json
import time
from open_swim.mqtt_client import MQTTClient
from open_swim.device_monitor import DeviceMonitor


def main() -> None:
    print("Open Swim running. Hello arm64 world!")
    

    
    # Set up MQTT connection callback
    def on_mqtt_connected():
        """Subscribe to test topic when connected."""
        print("[MQTT] Connected to broker, ready to publish/subscribe.")
        monitor.monitor_loop()
         # Publish a test message
        test_topic = "test/topic"
        test_message = "Hello from Open Swim!"
        mqtt_client.subscribe("test/topic")
        mqtt_client.publish(test_topic, test_message)
        print(f"Publishing message to topic '{test_topic}': {test_message}")
    
    def on_mqtt_message(topic: str, message: str):
        """Handle incoming MQTT messages."""
        print(f"[MQTT] Message received on topic '{topic}': {message}")
        
    # Create MQTT client
    mqtt_client = MQTTClient(on_connect_callback=on_mqtt_connected, on_message_callback=on_mqtt_message)
    
    
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
    
    try:
        mqtt_client.connect()
        # Keep the main thread alive to allow MQTT and device monitoring to run
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        mqtt_client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
