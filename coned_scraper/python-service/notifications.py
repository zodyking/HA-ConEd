"""
Mobile push notification system for Con Edison billing events.
Sends notifications to payees via Home Assistant companion app.
"""

import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


async def send_payee_notifications(event_type: str, data: Dict[str, Any]) -> int:
    """
    Send mobile notifications to all payees with notifications enabled.
    
    Args:
        event_type: One of 'new_bill', 'payment_received', 'due_reminder', 'balance_change'
        data: Dictionary with template variables for the message
        
    Returns:
        Number of notifications sent successfully
    """
    import aiohttp
    import db
    
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.debug("Not running as HA addon, skipping push notifications")
        return 0
    
    # Get notification config
    config = await db.get_notification_config(event_type)
    if not config:
        logger.warning(f"No notification config found for event type: {event_type}")
        return 0
    
    if not config.get("enabled"):
        logger.debug(f"Notifications disabled for event type: {event_type}")
        return 0
    
    # Get payees with notifications enabled
    payees = await db.get_payees_with_notifications()
    if not payees:
        logger.debug("No payees with notifications enabled")
        return 0
    
    # Format the message
    message = format_template(config["template"], data)
    title = config["title"]
    
    # Send to each payee
    sent_count = 0
    try:
        async with aiohttp.ClientSession() as session:
            for payee in payees:
                notify_service = payee.get("notify_service")
                if not notify_service:
                    continue
                
                try:
                    async with session.post(
                        f"http://supervisor/core/api/services/notify/{notify_service}",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "title": title,
                            "message": message
                        }
                    ) as resp:
                        if resp.status == 200:
                            sent_count += 1
                            logger.info(f"Sent {event_type} notification to {payee['name']}")
                        else:
                            logger.warning(f"Failed to send notification to {notify_service}: {resp.status}")
                except Exception as e:
                    logger.error(f"Error sending notification to {notify_service}: {e}")
    except Exception as e:
        logger.error(f"Failed to send notifications: {e}")
    
    if sent_count > 0:
        await db.add_log("info", f"Sent {event_type} notification to {sent_count} device(s)")
    
    return sent_count


def format_template(template: str, data: Dict[str, Any]) -> str:
    """Replace template variables with actual values."""
    message = template
    for key, value in data.items():
        placeholder = f"{{{key}}}"
        message = message.replace(placeholder, str(value) if value is not None else "N/A")
    return message


async def notify_new_bill(
    amount: str,
    due_date: str,
    month_range: str
) -> int:
    """Send new bill notification to all enabled payees."""
    return await send_payee_notifications("new_bill", {
        "amount": amount,
        "due_date": due_date,
        "month_range": month_range,
    })


async def notify_payment_received(
    amount: str,
    balance: str,
    payee_name: Optional[str] = None
) -> int:
    """Send payment received notification to all enabled payees."""
    return await send_payee_notifications("payment_received", {
        "amount": amount,
        "balance": balance,
        "payee_name": payee_name or "Unknown",
    })


async def notify_balance_change(
    old_balance: str,
    new_balance: str
) -> int:
    """Send balance change notification to all enabled payees."""
    return await send_payee_notifications("balance_change", {
        "old_balance": old_balance,
        "new_balance": new_balance,
    })


async def notify_due_reminder(
    amount: str,
    due_date: str,
    days_until: int
) -> int:
    """Send due date reminder notification to all enabled payees."""
    return await send_payee_notifications("due_reminder", {
        "amount": amount,
        "due_date": due_date,
        "days_until": str(days_until),
    })


async def check_and_send_due_reminders() -> int:
    """
    Check for upcoming bill due dates and send reminders.
    Called by scheduler.
    """
    import db
    from datetime import datetime, timedelta
    
    # Get due reminder config
    config = await db.get_notification_config("due_reminder")
    if not config or not config.get("enabled"):
        return 0
    
    days_before = config.get("days_before_due") or 3
    
    # Get latest bill
    ledger = await db.get_ledger_data()
    if not ledger.get("latest_bill"):
        return 0
    
    latest_bill = ledger["latest_bill"]
    due_date_str = latest_bill.get("due_date")
    if not due_date_str:
        return 0
    
    try:
        # Parse due date (format: "Mar 15, 2026" or similar)
        due_date = None
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"]:
            try:
                due_date = datetime.strptime(due_date_str, fmt)
                break
            except ValueError:
                continue
        
        if not due_date:
            logger.warning(f"Could not parse due date: {due_date_str}")
            return 0
        
        # Check if we should send reminder
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        reminder_date = due_date - timedelta(days=days_before)
        
        if today.date() == reminder_date.date():
            days_until = (due_date - today).days
            return await notify_due_reminder(
                amount=latest_bill.get("bill_total", "N/A"),
                due_date=due_date_str,
                days_until=days_until
            )
    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")
    
    return 0
