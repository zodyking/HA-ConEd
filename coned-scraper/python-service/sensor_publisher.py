"""
Sensor publisher for Home Assistant MQTT integration
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from mqtt_client import get_mqtt_client
from change_detection import (
    get_account_balance, get_most_recent_bill, get_previous_bill, 
    get_last_payment, detect_changes
)

logger = logging.getLogger(__name__)

def publish_sensors(data: Dict[str, Any], timestamp: str = None):
    """
    Publish all sensors to MQTT after scraping.
    Only publishes sensors that have changed.
    """
    mqtt_client = get_mqtt_client()
    if not mqtt_client or not mqtt_client.connected:
        logger.warning("MQTT client not available, skipping sensor publishing")
        return
    
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    try:
        # Detect changes
        changes = detect_changes(data, timestamp)
        
        # Publish account balance
        account_balance = get_account_balance(data)
        if account_balance:
            if changes.get("account_balance", True):  # Always publish on first run
                mqtt_client.publish_account_balance(account_balance, timestamp)
                logger.info(f"Published account balance: {account_balance}")
        
        # Publish most recent bill
        most_recent_bill = get_most_recent_bill(data)
        if most_recent_bill:
            if changes.get("most_recent_bill", True):
                bill_amount = most_recent_bill.get("bill_total", "0")
                bill_date = most_recent_bill.get("bill_cycle_date") or most_recent_bill.get("bill_date", "")
                month_range = most_recent_bill.get("month_range", "")
                mqtt_client.publish_most_recent_bill(bill_amount, bill_date, month_range, timestamp)
                logger.info(f"Published most recent bill: {bill_amount}")
        
        # Publish previous bill
        previous_bill = get_previous_bill(data)
        if previous_bill:
            if changes.get("previous_bill", True):
                bill_amount = previous_bill.get("bill_total", "0")
                bill_date = previous_bill.get("bill_cycle_date") or previous_bill.get("bill_date", "")
                month_range = previous_bill.get("month_range", "")
                mqtt_client.publish_previous_bill(bill_amount, bill_date, month_range, timestamp)
                logger.info(f"Published previous bill: {bill_amount}")
        
        # Publish last payment
        last_payment = get_last_payment(data)
        if last_payment:
            if changes.get("last_payment", True):
                payment_amount = last_payment.get("amount", "0")
                payment_date = last_payment.get("bill_cycle_date", "")
                description = last_payment.get("description", "Payment Received")
                mqtt_client.publish_last_payment(payment_amount, payment_date, description, timestamp)
                logger.info(f"Published last payment: {payment_amount}")
        
        logger.info("Sensor publishing completed")
    except Exception as e:
        logger.error(f"Error publishing sensors: {e}", exc_info=True)

