"""
Change detection for sensor values
"""
import json
from typing import Optional, Dict, Any, Tuple
from database import get_latest_scraped_data

def extract_numeric_value(value_str: str) -> float:
    """Extract numeric value from string like '$123.45'"""
    try:
        return float(value_str.replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError, TypeError):
        return 0.0

def get_account_balance(data: Dict[str, Any]) -> Optional[str]:
    """Extract account balance from scraped data"""
    return data.get("account_balance")

def get_bills(data: Dict[str, Any]) -> list:
    """Extract bills from scraped data, sorted by date (newest first)"""
    bills = []
    bill_history = data.get("bill_history", {})
    ledger = bill_history.get("ledger", [])
    
    for entry in ledger:
        if entry.get("type") == "bill":
            bills.append(entry)
    
    # Sort by bill_cycle_date or bill_date (newest first)
    bills.sort(key=lambda x: x.get("bill_cycle_date") or x.get("bill_date") or "", reverse=True)
    return bills

def get_payments(data: Dict[str, Any]) -> list:
    """Extract payments from scraped data, sorted by date (newest first)"""
    payments = []
    bill_history = data.get("bill_history", {})
    ledger = bill_history.get("ledger", [])
    
    for entry in ledger:
        if entry.get("type") == "payment":
            payments.append(entry)
    
    # Sort by bill_cycle_date (newest first)
    payments.sort(key=lambda x: x.get("bill_cycle_date") or "", reverse=True)
    return payments

def get_most_recent_bill(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the most recent bill"""
    bills = get_bills(data)
    return bills[0] if bills else None

def get_previous_bill(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the previous (second most recent) bill"""
    bills = get_bills(data)
    return bills[1] if len(bills) > 1 else None

def get_last_payment(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the last (most recent) payment"""
    payments = get_payments(data)
    return payments[0] if payments else None

def detect_changes(new_data: Dict[str, Any], timestamp: str) -> Dict[str, bool]:
    """
    Detect changes in sensor values by comparing with previous data.
    Returns a dict indicating which sensors changed.
    """
    changes = {
        "account_balance": False,
        "most_recent_bill": False,
        "previous_bill": False,
        "last_payment": False
    }
    
    try:
        # Get previous data (latest 2 entries)
        previous_entries = get_latest_scraped_data(2)
        
        if len(previous_entries) < 2:
            # First or second scrape - all values are "new"
            changes["account_balance"] = True
            if get_most_recent_bill(new_data):
                changes["most_recent_bill"] = True
            if get_previous_bill(new_data):
                changes["previous_bill"] = True
            if get_last_payment(new_data):
                changes["last_payment"] = True
            return changes
        
        # Compare with previous data (second entry is the previous scrape)
        previous_data = previous_entries[1].get("data", {})
        
        # Check account balance change
        new_balance = get_account_balance(new_data)
        old_balance = get_account_balance(previous_data)
        if new_balance != old_balance:
            changes["account_balance"] = True
        
        # Check most recent bill change
        new_bill = get_most_recent_bill(new_data)
        old_bill = get_most_recent_bill(previous_data)
        if new_bill and old_bill:
            new_bill_date = new_bill.get("bill_cycle_date") or new_bill.get("bill_date")
            old_bill_date = old_bill.get("bill_cycle_date") or old_bill.get("bill_date")
            if new_bill_date != old_bill_date:
                changes["most_recent_bill"] = True
        elif new_bill and not old_bill:
            changes["most_recent_bill"] = True
        
        # Check previous bill change
        new_prev_bill = get_previous_bill(new_data)
        old_prev_bill = get_previous_bill(previous_data)
        if new_prev_bill and old_prev_bill:
            new_prev_bill_date = new_prev_bill.get("bill_cycle_date") or new_prev_bill.get("bill_date")
            old_prev_bill_date = old_prev_bill.get("bill_cycle_date") or old_prev_bill.get("bill_date")
            if new_prev_bill_date != old_prev_bill_date:
                changes["previous_bill"] = True
        elif new_prev_bill and not old_prev_bill:
            changes["previous_bill"] = True
        
        # Check last payment change
        new_payment = get_last_payment(new_data)
        old_payment = get_last_payment(previous_data)
        if new_payment and old_payment:
            new_payment_date = new_payment.get("bill_cycle_date")
            old_payment_date = old_payment.get("bill_cycle_date")
            if new_payment_date != old_payment_date:
                changes["last_payment"] = True
        elif new_payment and not old_payment:
            changes["last_payment"] = True
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error detecting changes: {e}")
        # On error, assume all changed to be safe
        changes = {k: True for k in changes.keys()}
    
    return changes

