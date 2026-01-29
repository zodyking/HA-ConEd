"""
MQTT client for publishing updates to Home Assistant
"""
import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

logger = logging.getLogger(__name__)

class MQTTClient:
    """MQTT client for publishing sensor data to Home Assistant"""
    
    def __init__(self, mqtt_url: str, username: Optional[str] = None, password: Optional[str] = None,
                 base_topic: str = "coned", qos: int = 1, retain: bool = True):
        """
        Initialize MQTT client
        
        Args:
            mqtt_url: MQTT broker URL (mqtt://host:port or mqtts://host:port)
            username: MQTT username (optional)
            password: MQTT password (optional)
            base_topic: Base topic prefix (default: "coned")
            qos: Quality of Service level (0, 1, or 2, default: 1)
            retain: Whether to retain messages (default: True)
        """
        if not MQTT_AVAILABLE:
            logger.warning("paho-mqtt not installed. MQTT functionality disabled.")
            self.enabled = False
            return
        
        self.enabled = True
        self.base_topic = base_topic
        self.qos = qos
        self.retain = retain
        self.client = None
        self.connected = False
        self._connect_lock = asyncio.Lock()
        
        # Parse MQTT URL
        if mqtt_url.startswith("mqtts://"):
            self.use_tls = True
            url = mqtt_url[8:]
        elif mqtt_url.startswith("mqtt://"):
            self.use_tls = False
            url = mqtt_url[7:]
        else:
            logger.error(f"Invalid MQTT URL format: {mqtt_url}. Must start with mqtt:// or mqtts://")
            self.enabled = False
            return
        
        # Parse host and port
        if ":" in url:
            host, port_str = url.split(":", 1)
            try:
                self.port = int(port_str)
            except ValueError:
                logger.error(f"Invalid port in MQTT URL: {port_str}")
                self.enabled = False
                return
        else:
            host = url
            self.port = 8883 if self.use_tls else 1883
        
        self.host = host
        self.username = username
        self.password = password
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=f"coned_scraper_{datetime.now().timestamp()}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        if self.use_tls:
            self.client.tls_set()
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when MQTT client connects"""
        if rc == 0:
            self.connected = True
            logger.info(f"MQTT connected to {self.host}:{self.port}")
        else:
            self.connected = False
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when MQTT client disconnects"""
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT disconnected unexpectedly (code {rc}). Will attempt to reconnect.")
    
    async def connect(self):
        """Connect to MQTT broker"""
        if not self.enabled:
            return False
        
        async with self._connect_lock:
            if self.connected:
                return True
            
            try:
                # Run connection in thread pool since paho-mqtt is synchronous
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.client.connect, self.host, self.port, 60)
                self.client.loop_start()
                
                # Wait a bit for connection to establish
                await asyncio.sleep(0.5)
                return self.connected
            except Exception as e:
                logger.error(f"Failed to connect to MQTT broker: {str(e)}")
                return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting MQTT: {str(e)}")
    
    async def ensure_connected(self):
        """Ensure MQTT client is connected, reconnect if needed"""
        if not self.enabled:
            return False
        
        if not self.connected:
            return await self.connect()
        return True
    
    def _extract_numeric(self, value: str) -> str:
        """Extract numeric value from string (e.g., '$123.45' -> '123.45')"""
        if not value:
            return "0"
        # Remove currency symbols and commas, extract number
        cleaned = re.sub(r'[^\d.-]', '', str(value))
        try:
            num = float(cleaned)
            return str(num)
        except ValueError:
            return "0"
    
    async def publish(self, topic_suffix: str, payload: str, json_payload: Optional[Dict[str, Any]] = None):
        """
        Publish message to MQTT topic
        
        Args:
            topic_suffix: Topic suffix (e.g., "account_balance")
            payload: String payload for numeric topic
            json_payload: Optional JSON payload for _json topic
        """
        if not self.enabled:
            return
        
        if not await self.ensure_connected():
            logger.warning(f"MQTT not connected, skipping publish to {topic_suffix}")
            return
        
        try:
            # Publish numeric value
            topic = f"{self.base_topic}/{topic_suffix}"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.publish,
                topic,
                payload,
                self.qos,
                self.retain
            )
            
            # Publish JSON payload if provided
            if json_payload:
                json_topic = f"{self.base_topic}/{topic_suffix}_json"
                json_str = json.dumps(json_payload)
                await loop.run_in_executor(
                    None,
                    self.client.publish,
                    json_topic,
                    json_str,
                    self.qos,
                    self.retain
                )
            
            logger.debug(f"MQTT published to {topic}: {payload}")
        except Exception as e:
            logger.warning(f"Failed to publish MQTT message to {topic_suffix}: {str(e)}")
    
    async def publish_account_balance(self, balance: str, timestamp: Optional[str] = None):
        """Publish account balance update"""
        numeric_value = self._extract_numeric(balance)
        json_payload = {
            "event_type": "account_balance",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "account_balance": float(numeric_value),
                "account_balance_raw": balance,
                "timestamp": timestamp or utc_now_iso()
            }
        }
        await self.publish("account_balance", numeric_value, json_payload)
    
    async def publish_latest_bill(self, bill_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Publish latest bill update"""
        numeric_value = self._extract_numeric(bill_data.get("bill_total", "0"))
        json_payload = {
            "event_type": "latest_bill",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "bill_total": bill_data.get("bill_total"),
                "bill_cycle_date": bill_data.get("bill_cycle_date"),
                "month_range": bill_data.get("month_range"),
                "bill_date": bill_data.get("bill_date"),
                "timestamp": timestamp or utc_now_iso()
            }
        }
        await self.publish("latest_bill", numeric_value, json_payload)
    
    async def publish_previous_bill(self, bill_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Publish previous bill update"""
        numeric_value = self._extract_numeric(bill_data.get("bill_total", "0"))
        json_payload = {
            "event_type": "previous_bill",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "bill_total": bill_data.get("bill_total"),
                "bill_cycle_date": bill_data.get("bill_cycle_date"),
                "month_range": bill_data.get("month_range"),
                "bill_date": bill_data.get("bill_date"),
                "timestamp": timestamp or utc_now_iso()
            }
        }
        await self.publish("previous_bill", numeric_value, json_payload)
    
    async def publish_last_payment(self, payment_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Publish last payment update"""
        numeric_value = self._extract_numeric(payment_data.get("amount", "0"))
        json_payload = {
            "event_type": "last_payment",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "amount": payment_data.get("amount"),
                "payment_date": payment_data.get("payment_date"),
                "bill_cycle_date": payment_data.get("bill_cycle_date"),
                "description": payment_data.get("description"),
                "timestamp": timestamp or utc_now_iso()
            }
        }
        await self.publish("last_payment", numeric_value, json_payload)
    
    async def publish_bill_pdf_url(self, pdf_url: str, timestamp: Optional[str] = None):
        """Publish bill PDF URL for Home Assistant"""
        json_payload = {
            "event_type": "bill_pdf_url",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "pdf_url": pdf_url,
                "timestamp": timestamp or utc_now_iso()
            }
        }
        await self.publish("bill_pdf_url", pdf_url, json_payload)

    async def publish_payee_summary(self, payee_data: list, bill_info: Dict[str, Any], timestamp: Optional[str] = None):
        """
        Publish payee summary for the most recent billing period
        
        Args:
            payee_data: List of payee summaries with name, amount_paid, share_of_bill
            bill_info: Bill metadata (bill_total, bill_cycle_date, etc.)
            timestamp: Optional timestamp override
        """
        # Build payee summary for MQTT
        payees = []
        for p in payee_data:
            paid = p.get('amount_paid', 0) or 0
            share = p.get('share_of_bill', 0) or 0
            diff = paid - share
            
            if abs(diff) < 0.01:
                status = "paid"
            elif diff > 0:
                status = "overpaid"
            else:
                status = "underpaid"
            
            payees.append({
                "name": p.get('name', 'Unknown'),
                "responsibility_percent": p.get('responsibility_percent', 0),
                "amount_paid": round(paid, 2),
                "amount_due": round(share, 2),
                "difference": round(diff, 2),
                "status": status
            })
        
        json_payload = {
            "event_type": "payee_summary",
            "timestamp": timestamp or utc_now_iso(),
            "data": {
                "bill_cycle_date": bill_info.get('bill_cycle_date', ''),
                "bill_total": bill_info.get('bill_total', 0),
                "total_paid": bill_info.get('total_paid', 0),
                "bill_balance": bill_info.get('bill_balance', 0),
                "bill_status": bill_info.get('bill_status', 'unknown'),
                "payees": payees,
                "timestamp": timestamp or utc_now_iso()
            }
        }
        
        # Publish as JSON only (no simple numeric value makes sense here)
        await self.publish("payee_summary", json.dumps(json_payload), json_payload)


# Global MQTT client instance
_mqtt_client: Optional[MQTTClient] = None

def init_mqtt_client(mqtt_url: str = "", username: str = "", password: str = "",
                     base_topic: str = "coned", qos: int = 1, retain: bool = True) -> Optional[MQTTClient]:
    """Initialize MQTT client from configuration"""
    global _mqtt_client
    
    if not mqtt_url or not mqtt_url.strip():
        logger.info("MQTT URL not configured, MQTT client disabled")
        _mqtt_client = None
        return None
    
    try:
        _mqtt_client = MQTTClient(
            mqtt_url.strip(),
            username.strip() if username else None,
            password.strip() if password else None,
            base_topic.strip() if base_topic else "coned",
            qos,
            retain
        )
        logger.info(f"MQTT client initialized for {mqtt_url}")
        return _mqtt_client
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {str(e)}")
        _mqtt_client = None
        return None

def get_mqtt_client() -> Optional[MQTTClient]:
    """Get the global MQTT client instance"""
    return _mqtt_client


