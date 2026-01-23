"""
MQTT integration for Home Assistant sensor publishing
"""
import paho.mqtt.client as mqtt
import json
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class MQTTClient:
    """MQTT client for publishing sensor data to Home Assistant"""
    
    def __init__(self, host: str = "core-mosquitto", port: int = 1883, 
                 username: Optional[str] = None, password: Optional[str] = None,
                 topic_prefix: str = "coned"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=f"{self.topic_prefix}_scraper")
            
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            try:
                self.client.connect(self.host, self.port, keepalive=60)
                self.client.loop_start()
                # Wait a bit for connection
                import time
                time.sleep(1)
                return self.connected
            except Exception as e:
                logger.error(f"Failed to connect to MQTT broker at {self.host}:{self.port}: {e}")
                return False
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker, return code {rc}")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def publish_sensor(self, sensor_name: str, value: Any, attributes: Optional[Dict[str, Any]] = None):
        """Publish sensor state to MQTT"""
        if not self.connected or not self.client:
            logger.warning("MQTT not connected, skipping sensor publish")
            return False
        
        try:
            # State topic
            state_topic = f"{self.topic_prefix}/{sensor_name}/state"
            
            # Publish state - always as string for numeric values
            if isinstance(value, (int, float)):
                payload = str(value)
            elif isinstance(value, dict):
                payload = json.dumps(value)
            else:
                payload = str(value)
            
            result = self.client.publish(state_topic, payload, qos=1, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published {sensor_name} = {value}")
            else:
                logger.error(f"Failed to publish {sensor_name}, return code {result.rc}")
            
            # Publish attributes if provided
            if attributes:
                attrs_topic = f"{self.topic_prefix}/{sensor_name}/attributes"
                attrs_payload = json.dumps(attributes)
                self.client.publish(attrs_topic, attrs_payload, qos=1, retain=True)
            
            # Publish availability
            availability_topic = f"{self.topic_prefix}/{sensor_name}/availability"
            self.client.publish(availability_topic, "online", qos=1, retain=True)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Error publishing sensor {sensor_name}: {e}")
            return False
    
    def publish_account_balance(self, balance: str, timestamp: str):
        """Publish account balance sensor"""
        # Extract numeric value from balance string (e.g., "$123.45" -> 123.45)
        try:
            balance_value = float(balance.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            balance_value = 0.0
        
        attributes = {
            "timestamp": timestamp,
            "raw_value": balance
        }
        
        return self.publish_sensor("account_balance", balance_value, attributes)
    
    def publish_most_recent_bill(self, bill_amount: str, bill_date: str, month_range: str, timestamp: str):
        """Publish most recent bill amount sensor"""
        try:
            bill_value = float(bill_amount.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            bill_value = 0.0
        
        attributes = {
            "bill_date": bill_date,
            "month_range": month_range,
            "timestamp": timestamp,
            "raw_value": bill_amount
        }
        
        return self.publish_sensor("most_recent_bill", bill_value, attributes)
    
    def publish_previous_bill(self, bill_amount: str, bill_date: str, month_range: str, timestamp: str):
        """Publish previous bill amount sensor"""
        try:
            bill_value = float(bill_amount.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            bill_value = 0.0
        
        attributes = {
            "bill_date": bill_date,
            "month_range": month_range,
            "timestamp": timestamp,
            "raw_value": bill_amount
        }
        
        return self.publish_sensor("previous_bill", bill_value, attributes)
    
    def publish_last_payment(self, payment_amount: str, payment_date: str, description: str, timestamp: str):
        """Publish last payment sensor"""
        try:
            payment_value = float(payment_amount.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            payment_value = 0.0
        
        attributes = {
            "payment_date": payment_date,
            "description": description,
            "timestamp": timestamp,
            "raw_value": payment_amount
        }
        
        return self.publish_sensor("last_payment", payment_value, attributes)

# Global MQTT client instance
_mqtt_client: Optional[MQTTClient] = None

def init_mqtt_client(host: str = None, port: int = None, username: str = None, 
                     password: str = None, topic_prefix: str = None) -> MQTTClient:
    """Initialize MQTT client from environment variables or parameters"""
    global _mqtt_client
    
    # Get from environment variables (Home Assistant addon) or use parameters
    host = host or os.getenv("MQTT_HOST", "core-mosquitto")
    port = port or int(os.getenv("MQTT_PORT", "1883"))
    username = username or os.getenv("MQTT_USER", "")
    password = password or os.getenv("MQTT_PASSWORD", "")
    topic_prefix = topic_prefix or os.getenv("MQTT_TOPIC_PREFIX", "coned")
    
    _mqtt_client = MQTTClient(host, port, username if username else None, 
                              password if password else None, topic_prefix)
    
    if _mqtt_client.connect():
        logger.info("MQTT client initialized successfully")
    else:
        logger.warning("MQTT client failed to connect, sensors will not be published")
    
    return _mqtt_client

def get_mqtt_client() -> Optional[MQTTClient]:
    """Get the global MQTT client instance"""
    return _mqtt_client

