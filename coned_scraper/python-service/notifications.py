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
    Title/message from notification config payment_claim_prompt (editable in Settings).
    Actions: Yes (CONED_CLAIM_YES_<payment_id>_<payee_id>), No (CONED_CLAIM_NO_<payment_id>_<payee_id>)
    """
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("payment_claim_prompt")
    if cfg and not cfg.get("enabled", True):
        logger.debug("payment_claim_prompt notifications disabled, skipping claim request sends")
        return 0

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.debug("Not running as HA addon, skipping payment claim notifications")
        return 0

    payment_id = payment.get("id")
    amount = payment.get("amount", "N/A")
    payment_date = payment.get("payment_date", "N/A")
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Payment to claim")
        message = format_template(cfg.get("template") or "", {"amount": amount, "payment_date": payment_date})
    else:
        title = ensure_con_edison_title("Payment to claim")
        message = f"Did you make the {amount} payment on {payment_date}? (Tap & Hold to respond)"
    
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


async def _notify_one_device(
    session,
    token: str,
    notify_service: str,
    title: str,
    message: str,
    data_payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """Send a single mobile_app notify via Supervisor API."""
    body: Dict[str, Any] = {"title": title, "message": message}
    if data_payload:
        body["data"] = data_payload
    try:
        async with session.post(
            f"http://supervisor/core/api/services/notify/{notify_service}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
        ) as resp:
            if resp.status == 200:
                return True
            logger.warning("notify %s failed: %s", notify_service, resp.status)
    except Exception as e:
        logger.error("notify %s error: %s", notify_service, e)
    return False


async def send_petition_assignee_question(
    assignee: Dict[str, Any],
    petitioner_name: str,
    payment: Dict[str, Any],
    petitioner_payee_id: int,
) -> bool:
    """
    Notify the payee currently assigned to the payment (assignee) with Yes/No.
    YES = assignee confirms they made the payment (no reassignment).
    NO = payment is reassigned to the petitioner.
    """
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_assignee_question")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_assignee_question disabled, skipping petition question notify")
        return False

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.debug("Not running as HA addon, skipping petition notification")
        return False
    notify_service = assignee.get("notify_service")
    if not notify_service:
        logger.warning("Assignee has no notify_service; cannot send petition question")
        return False
    payment_id = payment.get("id")
    assignee_id = assignee.get("id")
    if not payment_id or not assignee_id:
        return False
    amount = payment.get("amount", "N/A")
    payment_date = payment.get("payment_date", "N/A")
    tmpl_data = {
        "petitioner_name": petitioner_name,
        "amount": amount,
        "payment_date": payment_date,
    }
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Payment petition")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Payment petition")
        message = (
            f"{petitioner_name} has requested a payment petition for payment made on {payment_date} "
            f"in the amount of {amount}. Are you sure you made this payment? (Tap & hold to respond)"
        )
    data_payload = {
        "actions": [
            {
                "action": f"CONED_PETITION_YES_{payment_id}_{assignee_id}_{petitioner_payee_id}",
                "title": "Yes",
            },
            {
                "action": f"CONED_PETITION_NO_{payment_id}_{assignee_id}_{petitioner_payee_id}",
                "title": "No",
            },
        ],
        "tag": f"coned_petition_{payment_id}_{petitioner_payee_id}",
        "ttl": 0,
        "priority": "high",
    }
    try:
        async with aiohttp.ClientSession() as session:
            ok = await _notify_one_device(
                session, token, notify_service, title, message, data_payload
            )
            if ok:
                await db.add_log("info", f"Sent petition question to assignee payee id {assignee_id}")
            return ok
    except Exception as e:
        logger.error("send_petition_assignee_question failed: %s", e)
        return False


async def notify_petition_assignee_confirmed(
    assignee: Dict[str, Any],
    petitioner: Dict[str, Any],
    payee_name: str,
    amount: str,
    payment_date: str,
) -> int:
    """
    Inform assignee and petitioner that assignee is sure they made the payment; ledger unchanged.
    """
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_resolved_no_change")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_resolved_no_change disabled, skipping dual notify")
        return 0

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return 0
    tmpl_data = {"payee_name": payee_name, "amount": amount, "payment_date": payment_date}
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Payment petition resolved")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Payment petition resolved")
        message = (
            f"{payee_name} is sure they made the payment posted on {payment_date}, "
            f"in the amount of {amount}. No changes have been made."
        )
    sent = 0
    seen = set()
    try:
        async with aiohttp.ClientSession() as session:
            for p in (assignee, petitioner):
                ns = p.get("notify_service")
                pid = p.get("id")
                if not ns or pid in seen:
                    continue
                seen.add(pid)
                if await _notify_one_device(session, token, ns, title, message):
                    sent += 1
    except Exception as e:
        logger.error("notify_petition_assignee_confirmed failed: %s", e)
    return sent


async def notify_petition_submitted(
    petitioner: Dict[str, Any],
    assignee_name: str,
    amount: str,
    payment_date: str,
) -> bool:
    """Notify the petitioner that their petition request was sent to the assignee."""
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_submitted")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_submitted disabled, skipping notify")
        return False

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return False

    notify_service = petitioner.get("notify_service")
    if not notify_service:
        logger.debug("Petitioner has no notify_service, skipping petition_submitted")
        return False

    tmpl_data = {"amount": amount, "payment_date": payment_date, "assignee_name": assignee_name}
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Petition Sent")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Petition Sent")
        message = f"Your petition for the {amount} payment on {payment_date} was sent to {assignee_name}."

    try:
        async with aiohttp.ClientSession() as session:
            return await _notify_one_device(session, token, notify_service, title, message)
    except Exception as e:
        logger.error("notify_petition_submitted failed: %s", e)
        return False


async def notify_petition_reassigned_to_you(
    petitioner: Dict[str, Any],
    amount: str,
    payment_date: str,
) -> bool:
    """Notify the petitioner that the payment has been reassigned to them."""
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_reassigned_to_you")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_reassigned_to_you disabled, skipping notify")
        return False

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return False

    notify_service = petitioner.get("notify_service")
    if not notify_service:
        logger.debug("Petitioner has no notify_service, skipping petition_reassigned_to_you")
        return False

    tmpl_data = {"amount": amount, "payment_date": payment_date}
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Payment Reassigned")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Payment Reassigned")
        message = f"The {amount} payment on {payment_date} has been reassigned to you."

    try:
        async with aiohttp.ClientSession() as session:
            return await _notify_one_device(session, token, notify_service, title, message)
    except Exception as e:
        logger.error("notify_petition_reassigned_to_you failed: %s", e)
        return False


async def notify_petition_lost(
    assignee: Dict[str, Any],
    petitioner_name: str,
    amount: str,
    payment_date: str,
) -> bool:
    """Notify the original assignee that the payment was reassigned per their response."""
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_lost")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_lost disabled, skipping notify")
        return False

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return False

    notify_service = assignee.get("notify_service")
    if not notify_service:
        logger.debug("Assignee has no notify_service, skipping petition_lost")
        return False

    tmpl_data = {"amount": amount, "payment_date": payment_date, "petitioner_name": petitioner_name}
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Payment Reassigned")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Payment Reassigned")
        message = f"Per your response, the {amount} payment on {payment_date} was reassigned to {petitioner_name}."

    try:
        async with aiohttp.ClientSession() as session:
            return await _notify_one_device(session, token, notify_service, title, message)
    except Exception as e:
        logger.error("notify_petition_lost failed: %s", e)
        return False


async def notify_petition_cancelled(
    assignee: Dict[str, Any],
    petitioner: Dict[str, Any],
    amount: str,
    payment_date: str,
) -> int:
    """Notify both parties that a petition has been closed/cancelled."""
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    cfg = await db.get_notification_config("petition_cancelled")
    if cfg and not cfg.get("enabled", True):
        logger.debug("petition_cancelled disabled, skipping notify")
        return 0

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return 0

    tmpl_data = {"amount": amount, "payment_date": payment_date}
    if cfg:
        title = ensure_con_edison_title(cfg.get("title") or "Petition Closed")
        message = format_template(cfg.get("template") or "", tmpl_data)
    else:
        title = ensure_con_edison_title("Petition Closed")
        message = f"The petition for the {amount} payment on {payment_date} has been closed."

    sent = 0
    seen = set()
    try:
        async with aiohttp.ClientSession() as session:
            for p in (assignee, petitioner):
                if not p:
                    continue
                ns = p.get("notify_service")
                pid = p.get("id")
                if not ns or pid in seen:
                    continue
                seen.add(pid)
                if await _notify_one_device(session, token, ns, title, message):
                    sent += 1
    except Exception as e:
        logger.error("notify_petition_cancelled failed: %s", e)
    return sent


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


async def check_and_send_payee_balance_reminders() -> int:
    """
    Daily per-payee notification when underpaid on the latest bill.
    One send per payee per bill per calendar day (dedup).
    """
    import aiohttp
    import db

    await db.ensure_notification_configs_exist()
    config = await db.get_notification_config("payee_balance_reminder")
    if not config or not config.get("enabled"):
        return 0

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.debug("Not running as HA addon, skipping payee balance reminders")
        return 0

    summaries = await db.calculate_all_payee_balances()
    if not summaries:
        return 0
    latest = summaries[0]
    bill_id = latest.get("bill_id")
    if bill_id is None:
        return 0

    days_rem, end_display = await db.compute_days_remaining_in_billing_cycle(latest)
    days_str = str(days_rem) if days_rem is not None else "N/A"

    payees = await db.get_payees_with_notifications()
    if not payees:
        return 0

    title = ensure_con_edison_title(config.get("title") or "")
    template = config.get("template") or ""

    sent_count = 0
    try:
        async with aiohttp.ClientSession() as session:
            for payee in payees:
                pid = payee.get("id")
                ns = payee.get("notify_service")
                if not pid or not ns:
                    continue
                pr = next(
                    (p for p in (latest.get("payees") or []) if p.get("user_id") == pid),
                    None,
                )
                if not pr or pr.get("status") != "underpaid":
                    continue
                if await db.payee_balance_reminder_already_sent_today(pid, bill_id):
                    continue
                remaining = max(
                    0.0, (pr.get("amount_due") or 0) - (pr.get("amount_paid") or 0)
                )
                remaining_s = f"${remaining:.2f}"
                data = {
                    "payee_name": pr.get("name") or payee.get("name") or "",
                    "remaining_balance": remaining_s,
                    "days_remaining_cycle": days_str,
                    "billing_period_end": end_display,
                }
                message = format_template(template, data)
                try:
                    async with session.post(
                        f"http://supervisor/core/api/services/notify/{ns}",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json={"title": title, "message": message},
                    ) as resp:
                        if resp.status == 200:
                            sent_count += 1
                            await db.record_payee_balance_reminder_sent(pid, bill_id)
                            logger.info(
                                "Sent payee_balance_reminder to %s",
                                payee.get("name"),
                            )
                        else:
                            logger.warning(
                                "payee_balance_reminder failed for %s: %s",
                                ns,
                                resp.status,
                            )
                except Exception as e:
                    logger.error("payee_balance_reminder error for %s: %s", ns, e)
    except Exception as e:
        logger.error(f"check_and_send_payee_balance_reminders: {e}")

    if sent_count > 0:
        await db.add_log(
            "info",
            f"Sent payee_balance_reminder to {sent_count} device(s)",
        )
    return sent_count
