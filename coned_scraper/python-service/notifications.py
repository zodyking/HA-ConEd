"""
Mobile push notification system for Con Edison billing events.
Sends notifications to payees via Home Assistant companion app.
"""

import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def ensure_con_edison_title(title: str) -> str:
    """Ensure notification title includes Con Edison (safeguard for stale DB configs)."""
    if not title:
        return "Con Edison"
    if "con edison" in title.lower() or "conedison" in title.lower():
        return title
    return f"Con Edison: {title}"


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
    title = ensure_con_edison_title(config.get("title") or "")
    
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


async def notify_late_fee(late_fee_amount: str) -> int:
    """Send late fee notification to all enabled payees."""
    return await send_payee_notifications("late_fee", {
        "late_fee_amount": late_fee_amount,
    })


async def notify_payment_claimed(
    payee_name: str,
    amount: str,
    payment_date: str
) -> int:
    """Send payment claimed notification to all enabled payees (no prefix)."""
    return await send_payee_notifications("payment_claimed", {
        "payee_name": payee_name,
        "amount": amount,
        "payment_date": payment_date,
    })


async def notify_payment_unclaimed(
    payee_name: str,
    amount: str,
    payment_date: str
) -> int:
    """Send payment unclaimed notification to all enabled payees (no prefix)."""
    return await send_payee_notifications("payment_unclaimed", {
        "payee_name": payee_name,
        "amount": amount,
        "payment_date": payment_date,
    })


async def send_payment_claim_request(payment: Dict[str, Any], payees: List[Dict[str, Any]]) -> int:
    """
    Send per-payee claim notifications for an unverified payment.
    Title: "Payment to claim"
    Message: "Did you make the $X.XX payment on [date]?"
    Actions: Yes (CONED_CLAIM_YES_<payment_id>_<payee_id>), No (CONED_CLAIM_NO_<payment_id>_<payee_id>)
    Main tap does nothing; only Yes/No actions trigger the automation.
    """
    import aiohttp
    
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.debug("Not running as HA addon, skipping payment claim notifications")
        return 0
    
    payment_id = payment.get("id")
    amount = payment.get("amount", "N/A")
    payment_date = payment.get("payment_date", "N/A")
    title = ensure_con_edison_title("Payment to claim")
    message = f"Did you make the {amount} payment on {payment_date}?"
    
    sent_count = 0
    try:
        async with aiohttp.ClientSession() as session:
            for payee in payees:
                notify_service = payee.get("notify_service")
                if not notify_service:
                    continue
                payee_id = payee.get("id")
                if not payee_id:
                    continue
                # Actions: only Yes/No trigger events; main tap does nothing via tap_action: "none" or similar
                # HA mobile_app: data.actions with action IDs. Automation triggers on mobile_app_notification_action.
                data_payload = {
                    "actions": [
                        {"action": f"CONED_CLAIM_YES_{payment_id}_{payee_id}", "title": "Yes"},
                        {"action": f"CONED_CLAIM_NO_{payment_id}_{payee_id}", "title": "No"},
                    ],
                    "tag": f"coned_claim_{payment_id}_{payee_id}",
                    "ttl": 0,
                    "priority": "high",
                }
                try:
                    async with session.post(
                        f"http://supervisor/core/api/services/notify/{notify_service}",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "title": title,
                            "message": message,
                            "data": data_payload,
                        }
                    ) as resp:
                        if resp.status == 200:
                            sent_count += 1
                            logger.info(f"Sent claim request to {payee.get('name', 'payee')}")
                        else:
                            logger.warning(f"Failed to send claim notification to {notify_service}: {resp.status}")
                except Exception as e:
                    logger.error(f"Error sending claim notification to {notify_service}: {e}")
    except Exception as e:
        logger.error(f"Failed to send payment claim notifications: {e}")
    
    return sent_count


async def notify_due_reminder(
    amount: str,
    due_date: str,
    days_until: int
) -> int:
    """Send due date reminder notification to all enabled payees."""
    days_until_text = "today" if days_until == 0 else f"in {days_until} days"
    return await send_payee_notifications("due_reminder", {
        "amount": amount,
        "due_date": due_date,
        "days_until": str(days_until),
        "days_until_text": days_until_text,
    })


async def check_and_send_due_reminders() -> int:
    """
    Check for upcoming bill due dates and send reminders.
    
    Sends a reminder every day from (due_date - days_before) through due_date:
    - Day 3 before: "due in 3 days"
    - Day 2 before: "due in 2 days"
    - Day 1 before: "due in 1 day"
    - Due date: "due today"
    
    Skips if already sent for this bill today (avoids duplicates).
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
    bill_id = latest_bill.get("id")
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
        
        # Normalize to date for comparison
        from datetime import date
        today = date.today()
        due_date_date = due_date.date()
        reminder_start = due_date_date - timedelta(days=days_before)
        
        # Send if today is within [reminder_start, due_date] inclusive
        if reminder_start <= today <= due_date_date:
            # Avoid sending twice the same day
            if bill_id and await db.due_reminder_already_sent_today(bill_id):
                return 0
            
            days_until = (due_date_date - today).days  # 0 = due today
            days_until_text = "today" if days_until == 0 else f"in {days_until} days"
            
            sent = await send_payee_notifications("due_reminder", {
                "amount": latest_bill.get("bill_total", "N/A"),
                "due_date": due_date_str,
                "days_until": str(days_until),
                "days_until_text": days_until_text,
            })
            
            if sent > 0 and bill_id:
                await db.record_due_reminder_sent(bill_id)
            
            return sent
    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")
    
    return 0
