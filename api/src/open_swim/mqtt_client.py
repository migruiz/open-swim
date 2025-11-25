import os
import time
from typing import Callable, Optional
from dotenv import load_dotenv
import paho.mqtt.client as mqtt


class MQTTCallbacks:
    """Callbacks for MQTT events."""
    
    def __init__(self):
        self.on_connect_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_publish_callback: Optional[Callable] = None
    
    def set_on_connect(self, callback: Callable):
        """Set callback for connection events."""
        self.on_connect_callback = callback
    
    def set_on_message(self, callback: Callable):
        """Set callback for message events."""
        self.on_message_callback = callback
    
    def set_on_publish(self, callback: Callable):
        """Set callback for publish events."""
        self.on_publish_callback = callback


class MQTTClient:
    """Manages MQTT connection and messaging."""
    
    def __init__(self, callbacks: Optional[MQTTCallbacks] = None):
        self.callbacks = callbacks or MQTTCallbacks()
        self.client: Optional[mqtt.Client] = None
        self.broker_host: Optional[str] = None
        self.broker_port: int = 1883
        
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Internal callback when the client connects to the broker."""
        if rc == 0:
            print(f"Connected to MQTT broker successfully")
            if self.callbacks.on_connect_callback:
                self.callbacks.on_connect_callback(client, userdata, flags, rc, properties)
        else:
            print(f"Failed to connect, return code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Internal callback when a message is received."""
        print(f"Received message on topic '{msg.topic}': {msg.payload.decode()}")
        if self.callbacks.on_message_callback:
            self.callbacks.on_message_callback(client, userdata, msg)
    
    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """Internal callback when a message is published."""
        print(f"Message published with mid: {mid}")
        if self.callbacks.on_publish_callback:
            self.callbacks.on_publish_callback(client, userdata, mid, reason_code, properties)
    
    def connect(self, broker_uri: Optional[str] = None):
        """Connect to MQTT broker."""
        # Load environment variables if not already loaded
        load_dotenv()
        
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
        self.client.on_publish = self._on_publish
        
        # Connect to broker
        self.client.connect(self.broker_host, self.broker_port, 60)
        
        # Start the network loop in a background thread
        self.client.loop_start()
        
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
        if not self.client:
            raise RuntimeError("MQTT client not connected")
        
        return self.client.publish(topic, payload, qos=qos, retain=retain)
    
    def subscribe(self, topic: str, qos: int = 0):
        """Subscribe to a topic."""
        if not self.client:
            raise RuntimeError("MQTT client not connected")
        
        self.client.subscribe(topic, qos=qos)
        print(f"Subscribed to topic: {topic}")
