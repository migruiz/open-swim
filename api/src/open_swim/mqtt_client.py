import os
import time
from typing import Optional, Any, Protocol
import paho.mqtt.client as mqtt


class ConnectCallback(Protocol):
    """Protocol for MQTT connect callback."""
    def __call__(self) -> None:
        ...


class MessageCallback(Protocol):
    """Protocol for MQTT message callback."""
    def __call__(self, topic: str, message: Any) -> None:
        ...


class MQTTClient:
    """Manages MQTT connection and messaging."""
    
    def __init__(self, on_connect_callback: ConnectCallback, on_message_callback: MessageCallback):
        self.client: Optional[mqtt.Client] = None
        self.broker_host: Optional[str] = None
        self.broker_port: int = 1883
        self.on_connect_callback = on_connect_callback
        self.on_message_callback = on_message_callback
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Internal callback when the client connects to the broker."""
        if rc == 0:
            print(f"Connected to MQTT broker successfully")
            self.on_connect_callback()
                
        else:
            print(f"Failed to connect, return code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Internal callback when a message is received."""
        print(f"Received message on topic '{msg.topic}': {msg.payload.decode()}")
        self.on_message_callback(topic=msg.topic, message=msg.payload.decode())
                   
    def loop_forever(self, broker_uri: Optional[str] = None):
        """Connect to MQTT broker."""
        # Get broker URI from parameter or environment
        if not broker_uri:
            broker_uri = os.getenv("MQTT_BROKER_URI")
        
        if not broker_uri:
            raise ValueError("MQTT_BROKER_URI not provided and not set in environment variables")
        
        print(f"Connecting to MQTT broker: {broker_uri}")
        
        # Parse the URI (simple parsing for mqtt://host:port format)
        if broker_uri.startswith("mqtt://"):
            broker_uri = broker_uri[7:]  # Remove mqtt:// prefix
        
        parts = broker_uri.split(":")
        self.broker_host = parts[0]
        self.broker_port = int(parts[1]) if len(parts) > 1 else 1883
        
        # Create MQTT client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Connect to broker
        self.client.connect(self.broker_host, self.broker_port, 60)
        
        # Start the network loop in a background thread
        self.client.loop_forever()
        
        # Wait a moment for connection to establish
        time.sleep(2)
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            print("Disconnecting from MQTT broker...")
            self.client.loop_stop()
            self.client.disconnect()
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """Publish a message to a topic."""        
        return self.client.publish(topic, payload, qos=qos, retain=retain)
    
    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe to a topic."""
        self.client.subscribe(topic, qos=qos)
        print(f"Subscribed to topic: {topic}")
