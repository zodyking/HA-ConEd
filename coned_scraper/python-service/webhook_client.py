"""
Webhook client for sending updates to external services
"""
import aiohttp
import json
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()

logger = logging.getLogger(__name__)

class WebhookClient:
    """Webhook client for sending data updates to external services"""
    
    def __init__(self, webhook_config: Optional[Dict[str, str]] = None):
        """
        Initialize webhook client
        
        Args:
            webhook_config: Dictionary with webhook URLs for each event type:
                          - latest_bill: URL for latest bill updates
                          - previous_bill: URL for previous bill updates
                          - account_balance: URL for account balance updates
                          - last_payment: URL for last payment updates
        """
        if webhook_config:
            self.webhook_config = webhook_config
        else:
            self.webhook_config = {}
    
    def get_webhook_url(self, event_type: str) -> Optional[str]:
        """Get webhook URL for a specific event type"""
        return self.webhook_config.get(event_type)
    
    async def send_update(self, event_type: str, data: Dict[str, Any], timestamp: Optional[str] = None):
        """
        Send webhook update to the appropriate URL for the event type
        
        Args:
            event_type: Type of event (e.g., "latest_bill", "previous_bill", "account_balance", "last_payment")
            data: Data payload to send
            timestamp: Optional timestamp (defaults to current time)
        """
        webhook_url = self.get_webhook_url(event_type)
        
        if not webhook_url:
            logger.debug(f"No webhook URL configured for {event_type}, skipping webhook send")
            return
        
        if not timestamp:
            timestamp = utc_now_iso()
        
        payload = {
            "event_type": event_type,
            "timestamp": timestamp,
            "data": data
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(f"Webhook sent successfully to {webhook_url}: {event_type}")
                    else:
                        response_text = await response.text()
                        logger.warning(
                            f"Webhook failed to {webhook_url}: {response.status} - {response_text}"
                        )
        except Exception as e:
            logger.error(f"Error sending webhook to {webhook_url}: {str(e)}")
    
    async def send_account_balance(self, balance: str, timestamp: Optional[str] = None):
        """Send account balance update"""
        # Extract numeric value from balance string (e.g., "$123.45" -> 123.45)
        try:
            balance_value = float(balance.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            balance_value = 0.0
        
        data = {
            "account_balance": balance_value,
            "account_balance_raw": balance,
            "timestamp": timestamp or utc_now_iso()
        }
        
        await self.send_update("account_balance", data, timestamp)
    
    async def send_latest_bill(self, bill_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Send latest bill update"""
        data = {
            "bill_total": bill_data.get("bill_total"),
            "bill_cycle_date": bill_data.get("bill_cycle_date"),
            "month_range": bill_data.get("month_range"),
            "bill_date": bill_data.get("bill_date"),
            "timestamp": timestamp or utc_now_iso()
        }
        
        await self.send_update("latest_bill", data, timestamp)
    
    async def send_previous_bill(self, bill_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Send previous bill update"""
        data = {
            "bill_total": bill_data.get("bill_total"),
            "bill_cycle_date": bill_data.get("bill_cycle_date"),
            "month_range": bill_data.get("month_range"),
            "bill_date": bill_data.get("bill_date"),
            "timestamp": timestamp or utc_now_iso()
        }
        
        await self.send_update("previous_bill", data, timestamp)
    
    async def send_last_payment(self, payment_data: Dict[str, Any], timestamp: Optional[str] = None):
        """Send last payment update"""
        data = {
            "amount": payment_data.get("amount"),
            "payment_date": payment_data.get("payment_date"),
            "bill_cycle_date": payment_data.get("bill_cycle_date"),
            "description": payment_data.get("description"),
            "timestamp": timestamp or utc_now_iso()
        }
        
        await self.send_update("last_payment", data, timestamp)

# Global webhook client instance
_webhook_client: Optional[WebhookClient] = None

def init_webhook_client(webhook_config: Optional[Dict[str, str]] = None) -> WebhookClient:
    """Initialize webhook client from configuration"""
    global _webhook_client
    
    if webhook_config:
        _webhook_client = WebhookClient(webhook_config)
    else:
        _webhook_client = WebhookClient()
    
    configured_webhooks = [k for k, v in (_webhook_client.webhook_config or {}).items() if v]
    if configured_webhooks:
        logger.info(f"Webhook client initialized with URLs for: {', '.join(configured_webhooks)}")
    else:
        logger.info("Webhook client initialized but no URLs configured")
    
    return _webhook_client

def get_webhook_client() -> Optional[WebhookClient]:
    """Get the global webhook client instance"""
    return _webhook_client

def has_data_changed(current_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Compare current scrape data with previous scrape data to detect changes.
    Returns a dict indicating which fields have changed.
    """
    changes = {
        "account_balance": False,
        "latest_bill": False,
        "previous_bill": False,
        "last_payment": False
    }
    
    # If no previous data, everything is new
    if not previous_data:
        return {k: True for k in changes.keys()}
    
    # Compare account balance
    current_balance = current_data.get("account_balance", "")
    previous_balance = previous_data.get("account_balance", "")
    if current_balance != previous_balance:
        changes["account_balance"] = True
        logger.info(f"Account balance changed: {previous_balance} → {current_balance}")
    
    # Compare bill history
    current_history = current_data.get("bill_history", {})
    previous_history = previous_data.get("bill_history", {})
    
    current_ledger = current_history.get("ledger", [])
    previous_ledger = previous_history.get("ledger", [])
    
    # Extract bills and payments
    current_bills = [item for item in current_ledger if item.get("type") == "bill"]
    previous_bills = [item for item in previous_ledger if item.get("type") == "bill"]
    
    current_payments = [item for item in current_ledger if item.get("type") == "payment"]
    previous_payments = [item for item in previous_ledger if item.get("type") == "payment"]
    
    # Compare latest bill
    if len(current_bills) > 0 and len(previous_bills) > 0:
        current_bill = current_bills[0]
        previous_bill = previous_bills[0]
        if (current_bill.get("bill_total") != previous_bill.get("bill_total") or
            current_bill.get("bill_cycle_date") != previous_bill.get("bill_cycle_date") or
            current_bill.get("bill_date") != previous_bill.get("bill_date")):
            changes["latest_bill"] = True
            logger.info(f"Latest bill changed: {previous_bill.get('bill_total')} → {current_bill.get('bill_total')}")
    elif len(current_bills) > 0 and len(previous_bills) == 0:
        changes["latest_bill"] = True
        logger.info("New latest bill detected")
    
    # Compare previous bill
    if len(current_bills) > 1 and len(previous_bills) > 1:
        current_prev_bill = current_bills[1]
        previous_prev_bill = previous_bills[1]
        if (current_prev_bill.get("bill_total") != previous_prev_bill.get("bill_total") or
            current_prev_bill.get("bill_cycle_date") != previous_prev_bill.get("bill_cycle_date") or
            current_prev_bill.get("bill_date") != previous_prev_bill.get("bill_date")):
            changes["previous_bill"] = True
            logger.info(f"Previous bill changed")
    elif len(current_bills) > 1 and len(previous_bills) <= 1:
        changes["previous_bill"] = True
        logger.info("New previous bill detected")
    
    # Compare last payment
    if len(current_payments) > 0 and len(previous_payments) > 0:
        current_payment = current_payments[0]
        previous_payment = previous_payments[0]
        if (current_payment.get("amount") != previous_payment.get("amount") or
            current_payment.get("payment_date") != previous_payment.get("payment_date") or
            current_payment.get("bill_cycle_date") != previous_payment.get("bill_cycle_date")):
            changes["last_payment"] = True
            logger.info(f"Last payment changed: {previous_payment.get('amount')} → {current_payment.get('amount')}")
    elif len(current_payments) > 0 and len(previous_payments) == 0:
        changes["last_payment"] = True
        logger.info("New payment detected")
    
    return changes
