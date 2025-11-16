import os
import time
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when the client connects to the broker."""
    if rc == 0:
        print(f"Connected to MQTT broker successfully")
        # Subscribe to test topic
        test_topic =  "test/topic"
        client.subscribe(test_topic)
        print(f"Subscribed to topic: {test_topic}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    print(f"Received message on topic '{msg.topic}': {msg.payload.decode()}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    """Callback when a message is published."""
    print(f"Message published with mid: {mid}")

def main() -> None:
    print("Open Swim running. Hello arm64 world!")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get MQTT broker URI from environment variable
    broker_uri = os.getenv("MQTT_BROKER_URI")
    if not broker_uri:
        print("Error: MQTT_BROKER_URI not set in environment variables")
        return
    
    print(f"Connecting to MQTT broker: {broker_uri}")
    
    # Parse the URI (simple parsing for mqtt://host:port format)
    if broker_uri.startswith("mqtt://"):
        broker_uri = broker_uri[7:]  # Remove mqtt:// prefix
    
    parts = broker_uri.split(":")
    broker_host = parts[0]
    broker_port = int(parts[1]) if len(parts) > 1 else 1883
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    
    try:
        # Connect to broker
        client.connect(broker_host, broker_port, 60)
        
        # Start the network loop in a background thread
        client.loop_start()
        
        # Wait a moment for connection to establish
        time.sleep(2)
        
        # Publish a test message
        test_topic = "test/topic"
        test_message = "Hello from Open Swim!"
        result = client.publish(test_topic, test_message)
        print(f"Publishing message to topic '{test_topic}': {test_message}")
        
        # Keep the program running to receive messages
        print("Listening for messages... Press Ctrl+C to exit")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDisconnecting from MQTT broker...")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
