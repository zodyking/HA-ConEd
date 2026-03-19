from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pyotp
import json
import os
import time
import logging
from pathlib import Path
from cryptography.fernet import Fernet
import base64
import hashlib
import asyncio
from datetime import datetime, timedelta, timezone

def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()
# Database module (Prisma ORM with PostgreSQL)
import db

app = FastAPI(title="Con Edison API")

# Code version for deployment verification
CODE_VERSION = "1.3.47"

@app.on_event("startup")
async def startup():
    """Connect to PostgreSQL database on startup (with retries for startup race)"""
    for attempt in range(10):
        try:
            await db.connect()
            return
        except Exception as e:
            if attempt < 9:
                logging.warning(f"DB connect attempt {attempt + 1}/10 failed: {e}, retrying in 2s...")
                await asyncio.sleep(2)
            else:
                raise

@app.on_event("shutdown")
async def shutdown():
    """Disconnect from database on shutdown"""
    await db.disconnect()

@app.get("/api/version")
async def get_version():
    """Simple endpoint to verify code deployment"""
    return {"version": CODE_VERSION, "database": "postgresql"}

@app.get("/api/db-status")
async def get_db_status():
    """Check database connection and return status"""
    try:
        # Try to count logs as a simple query
        log_count = await db.get_log_count()
        bill_count = await db.get_bill_count()
        return {
            "connected": True,
            "database": "postgresql",
            "log_count": log_count,
            "bill_count": bill_count,
            "prisma_studio_port": 5555,
            "prisma_studio_url": "http://<your-ha-ip>:5555"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "database": "postgresql"
        }


def _parse_host_from_url(url: str) -> str | None:
    """Extract hostname from a URL (no port - caller appends :5555 for Prisma)."""
    if not url or not isinstance(url, str) or not url.strip():
        return None
    url = url.strip().rstrip("/")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else f"http://{url}")
        if parsed.hostname:
            return parsed.hostname
    except Exception:
        pass
    return None


@app.get("/api/prisma-url")
async def get_prisma_url(request: Request):
    """
    Return Prisma Studio URL using HA external_url if present, else internal_url, else request host.
    Prisma runs on port 5555 (HTTP).
    """
    host = None
    token = os.environ.get("SUPERVISOR_TOKEN")
    if token:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://supervisor/core/api/config",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        config = await resp.json()
                        external = config.get("external_url") or config.get("externalUrl")
                        internal = config.get("internal_url") or config.get("internalUrl")
                        # Prefer external if present and non-empty
                        url_str = (external or "").strip() or (internal or "").strip()
                        if url_str:
                            host = _parse_host_from_url(url_str)
        except Exception:
            pass
    if not host:
        # Fallback: use request host (X-Forwarded-Host from ingress, or Host)
        host = (
            request.headers.get("x-forwarded-host")
            or request.headers.get("X-Forwarded-Host")
            or request.headers.get("Host")
        )
        if host and ":" in host:
            host = host.split(":")[0]
    if not host:
        host = "localhost"
    return {"url": f"http://{host}:5555"}

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (safe in containerized environment)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration - use DATA_DIR env for addon (e.g. /config), else ./data
from data_config import DATA_DIR

CREDENTIALS_FILE = DATA_DIR / "credentials.json"
SETTINGS_FILE = DATA_DIR / "app_settings.json"
LAST_PAYMENT_STATE_FILE = DATA_DIR / "last_payment_state.json"
TTS_CONFIG_FILE = DATA_DIR / "tts_config.json"
TTS_PAYMENT_STATE_FILE = DATA_DIR / "tts_payment_state.json"
TTS_BILL_STATE_FILE = DATA_DIR / "tts_bill_state.json"
KEY_FILE = DATA_DIR / ".key"

# Default TTS settings (like Home-Energy)
DEFAULT_TTS_PREFIX = "Message from Con Edison."
DEFAULT_TTS_CONFIG = {
    "enabled": False,
    "media_player": "",
    "volume": 0.7,
    "language": "en",
    "prefix": DEFAULT_TTS_PREFIX,
    "wait_for_idle": True,
    "tts_service": "tts.google_translate_say",
    "messages": {
        "new_bill": "{prefix} Your new bill for {month_range} is now available. The total is {amount}, due {due_date}.",
        "payment_received": "{prefix} Your payment of {amount} has been received. Your account balance is now {balance}.",
        "late_fee": "{prefix} {late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date.",
        "payment_claimed": "{prefix} {payee_name} has claimed a payment of {amount} made on {payment_date}. If this was in error you can unclaim the payment via the account ledger.",
        "payment_unclaimed": "{prefix} {payee_name} has unclaimed a payment of {amount} made on {payment_date}. If this was in error you can claim the payment via the account ledger.",
    },
}

# Encryption key management
def get_or_create_key():
    """Get or create encryption key"""
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        return key

ENCRYPTION_KEY = get_or_create_key()
cipher = Fernet(ENCRYPTION_KEY)

# Automated scraping schedule
SCHEDULE_FILE = DATA_DIR / "schedule.json"
_scheduler_task = None
_scrape_running = False  # Track if a scrape is currently in progress
_due_reminder_task = None
_last_due_reminder_run_date = None

class ScheduleModel(BaseModel):
    enabled: bool
    frequency: int  # Frequency in seconds

async def load_schedule() -> dict:
    """Load automated scraping schedule from database"""
    try:
        data = await db.get_schedule_config_db()
        if not data:
            return {"enabled": False, "frequency": 3600, "last_scrape_end": None, "next_run": None}
        
        return {
            "enabled": data.get("enabled", False),
            "frequency": data.get("frequency", 3600),
            "last_scrape_end": data.get("last_scrape_end"),
            "next_run": data.get("next_run")
        }
    except Exception as e:
        logging.error(f"Failed to load schedule: {str(e)}")
        return {"enabled": False, "frequency": 3600, "last_scrape_end": None, "next_run": None}

async def save_schedule(enabled: bool, frequency: int, last_scrape_end: str = None, next_run: str = None):
    """Save automated scraping schedule to database"""
    # Load existing to preserve last_scrape_end if not provided
    existing = await load_schedule()
    
    schedule = {
        "enabled": enabled,
        "frequency": frequency,
        "last_scrape_end": last_scrape_end or existing.get("last_scrape_end"),
        "next_run": next_run or existing.get("next_run"),
        "updated_at": utc_now_iso()
    }
    await db.save_schedule_config_db(schedule)
    logging.info(f"Schedule saved: enabled={enabled}, frequency={frequency}s")

async def update_last_scrape_time():
    """Update last_scrape_end and calculate next_run after a successful scrape"""
    schedule = await load_schedule()
    now = datetime.now(timezone.utc)
    next_run = now + timedelta(seconds=schedule["frequency"])
    
    schedule["last_scrape_end"] = now.isoformat()
    schedule["next_run"] = next_run.isoformat()
    schedule["updated_at"] = utc_now_iso()
    await db.save_schedule_config_db(schedule)

async def run_scheduled_scrape():
    """Run a scheduled scrape"""
    global _scrape_running
    import time as time_module
    start_time = time_module.time()
    
    _scrape_running = True
    try:
        credentials = await load_credentials()
        if not credentials:
            await db.add_log("warning", "Scheduled scrape skipped: No credentials found")
            await db.add_scrape_history(False, "No credentials found", "credentials_check", 0)
            return
        
        from browser_automation import perform_login
        
        username = credentials["username"]
        password = credentials["password"]
        totp = pyotp.TOTP(credentials["totp_secret"])
        totp_code = totp.now()
        
        await db.add_log("info", "Starting scheduled scrape...")
        result = await perform_login(username, password, totp_code)
        success = result.get('success', False)
        scraped_data = result.get('data', {})
        
        if success and scraped_data:
            # ==========================================
            # TTS TRIGGERS AND NOTIFICATIONS
            # ==========================================
            
            # Check for new payment TTS trigger
            try:
                tts_payment_trigger, tts_payment_data, tts_payment_reason = await should_trigger_payment_tts()
                if tts_payment_trigger and tts_payment_data:
                    await db.add_log("info", f"Triggering payment TTS: {tts_payment_reason}")
                    from tts_scheduler import trigger_payment_received_tts
                    payment_amount = tts_payment_data.get("amount", "")
                    current_balance = scraped_data.get("account_balance", "")
                    payee_name = tts_payment_data.get("payee_name", "")
                    await trigger_payment_received_tts(payment_amount, current_balance, payee_name)
                    # Send push notification for payment
                    try:
                        from notifications import notify_payment_received
                        await notify_payment_received(
                            amount=payment_amount,
                            balance=current_balance,
                            payee_name=payee_name
                        )
                    except Exception as notify_e:
                        await db.add_log("warning", f"Failed to send payment notification: {notify_e}")
                else:
                    await db.add_log("debug", f"No payment TTS: {tts_payment_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger payment TTS: {tts_e}")
            
            # Check for new bill TTS trigger
            try:
                tts_bill_trigger, tts_bill_data, tts_bill_reason = await should_trigger_new_bill_tts()
                if tts_bill_trigger and tts_bill_data:
                    await db.add_log("info", f"Triggering new bill TTS: {tts_bill_reason}")
                    from tts_scheduler import trigger_new_bill_tts
                    await trigger_new_bill_tts(
                        bill_month_range=tts_bill_data.get("month_range", ""),
                        bill_total=tts_bill_data.get("bill_total", ""),
                        due_date=tts_bill_data.get("due_date", "")
                    )
                    # Send push notification for new bill
                    try:
                        from notifications import notify_new_bill
                        await notify_new_bill(
                            amount=tts_bill_data.get("bill_total", "N/A"),
                            due_date=tts_bill_data.get("due_date", "N/A"),
                            month_range=tts_bill_data.get("month_range", "N/A")
                        )
                    except Exception as notify_e:
                        await db.add_log("warning", f"Failed to send new bill notification: {notify_e}")
                else:
                    await db.add_log("debug", f"No bill TTS: {tts_bill_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger bill TTS: {tts_e}")
            
        # Due date reminders now run at configured time via due_reminder_scheduler_loop
        
        if success:
            # Auto-assign expired pending payments to default payee
            try:
                # Auto-assign expired pending payments
                await db.auto_assign_expired_pending_payments()
                result = {"message": "Auto-assigned expired pending payments"}
                if result.get('assigned', 0) > 0:
                    await db.add_log("info", result.get('message', 'Auto-assigned expired pending payments'))
            except Exception as auto_e:
                await db.add_log("warning", f"Auto-assign expired payments failed: {auto_e}")
            
            # Send payment claim requests for new unverified payments (notification-based assignment)
            try:
                pv = await get_payment_verification_settings()
                if pv.get("notification_claims_enabled", True) and pv.get("auto_send_claims_after_scrape", True):
                    from notifications import send_payment_claim_request
                    payments_to_claim = await db.get_unverified_payments_with_no_claim_responses()
                    payees = await db.get_payees_with_notifications()
                    if payments_to_claim and payees:
                        for payment in payments_to_claim:
                            sent = await send_payment_claim_request(payment, payees)
                            if sent > 0:
                                await db.add_log("info", f"Sent payment claim request to {sent} payee(s) for payment ${payment.get('amount_numeric', 0):.2f}")
            except Exception as claim_e:
                await db.add_log("warning", f"Payment claim notifications failed: {claim_e}")
        
        duration = time_module.time() - start_time
        await db.add_scrape_history(success, None if success else "Scrape failed", None, duration)
        await db.add_log("success", f"Scheduled scrape completed: {success}")
    except Exception as e:
        duration = time_module.time() - start_time
        error_msg = f"Scheduled scrape failed: {str(e)}"
        await db.add_scrape_history(False, error_msg, "unknown", duration)
        await db.add_log("error", error_msg)
        logging.error(error_msg)
    finally:
        _scrape_running = False

async def scheduler_loop():
    """Background scheduler loop - runs scrapes based on last_scrape_end + frequency"""
    while True:
        try:
            schedule = await load_schedule()
            
            if schedule["enabled"]:
                frequency = schedule["frequency"]
                next_run_str = schedule.get("next_run")
                
                # Calculate seconds until next run
                if next_run_str:
                    try:
                        next_run = datetime.fromisoformat(next_run_str.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        seconds_until_run = (next_run - now).total_seconds()
                    except:
                        seconds_until_run = 0
                else:
                    # No next_run set, run immediately then set it
                    seconds_until_run = 0
                
                if seconds_until_run > 0:
                    await db.add_log("info", f"Scheduler: Next scrape in {int(seconds_until_run)} seconds")
                    await asyncio.sleep(min(seconds_until_run, 60))  # Check at least every 60s
                    continue  # Re-check if it's time
                
                # Time to run!
                current_schedule = await load_schedule()
                if current_schedule["enabled"]:
                    await run_scheduled_scrape()
                    # Update next run time after scrape completes
                    await update_last_scrape_time()
            else:
                # If disabled, check every 60 seconds
                await asyncio.sleep(60)
        except Exception as e:
            error_msg = f"Scheduler error: {str(e)}"
            await db.add_log("error", error_msg)
            logging.error(error_msg)
            await asyncio.sleep(60)  # Wait before retrying

async def due_reminder_scheduler_loop():
    """Run due date reminders at the configured time each day."""
    global _last_due_reminder_run_date
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            config = await db.get_notification_config("due_reminder")
            if not config or not config.get("enabled"):
                continue
            send_time = config.get("reminder_send_time", "09:00")
            try:
                h, m = map(int, send_time.split(":")[:2])
            except (ValueError, IndexError):
                h, m = 9, 0
            now = datetime.now()
            if now.hour != h or now.minute != m:
                continue
            today = now.date()
            if _last_due_reminder_run_date == today:
                continue
            _last_due_reminder_run_date = today
            try:
                from notifications import check_and_send_due_reminders
                sent = await check_and_send_due_reminders()
                if sent > 0:
                    await db.add_log("info", f"Due reminder sent to {sent} device(s)")
            except Exception as e:
                await db.add_log("warning", f"Due reminder check failed: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Due reminder scheduler error: {e}")
            await asyncio.sleep(60)


async def claim_resend_scheduler_loop():
    """Resend payment claim notifications when all payees said No and delay has passed."""
    while True:
        try:
            await asyncio.sleep(900)  # Check every 15 minutes
            pv = await get_payment_verification_settings()
            if not pv.get("notification_claims_enabled", True):
                continue
            delay_hours = int(pv.get("claim_resend_delay_hours", 24))
            candidates = await db.get_payments_for_claim_resend(claim_resend_delay_hours=delay_hours)
            if not candidates:
                continue
            from notifications import send_payment_claim_request
            payees = await db.get_payees_with_notifications()
            if not payees:
                continue
            for payment in candidates:
                try:
                    await db.reset_claim_responses_for_resend(payment["id"])
                    sent = await send_payment_claim_request(payment, payees)
                    if sent > 0:
                        await db.add_log("info", f"Resent payment claim request for payment ${payment.get('amount_numeric', 0):.2f} (all had said No)")
                except Exception as e:
                    await db.add_log("warning", f"Claim resend failed for payment {payment.get('id')}: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Claim resend scheduler error: {e}")
            await asyncio.sleep(900)


async def restart_scheduler():
    """Restart the scheduler with current settings"""
    global _scheduler_task
    
    # Cancel existing task if running
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Start new scheduler task
    schedule = await load_schedule()
    if schedule["enabled"]:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        await db.add_log("info", "Scheduler restarted")
    else:
        await db.add_log("info", "Scheduler disabled")

# Start scheduler on app startup
_claim_resend_task = None

@app.on_event("startup")
async def startup_event():
    global _scheduler_task, _due_reminder_task, _claim_resend_task

    schedule = await load_schedule()
    if schedule["enabled"]:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        await db.add_log("info", f"Scheduler started with {schedule['frequency']}s frequency")

    _due_reminder_task = asyncio.create_task(due_reminder_scheduler_loop())
    await db.add_log("info", "Due reminder scheduler started")

    _claim_resend_task = asyncio.create_task(claim_resend_scheduler_loop())
    await db.add_log("info", "Claim resend scheduler started")

    # Start TTS scheduler
    try:
        from tts_scheduler import get_scheduler
        tts_scheduler = get_scheduler()
        await tts_scheduler.start()
        await db.add_log("info", "TTS scheduler started")
    except Exception as e:
        await db.add_log("warning", f"TTS scheduler initialization failed: {e}")
    
    # Initialize meter tracking service
    try:
        from meter_service import init_meter_service
        await init_meter_service()
        await db.add_log("info", "Meter tracking service initialized")
    except Exception as e:
        await db.add_log("warning", f"Meter tracking service initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global _scheduler_task, _due_reminder_task, _claim_resend_task
    if _claim_resend_task and not _claim_resend_task.done():
        _claim_resend_task.cancel()
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    if _due_reminder_task and not _due_reminder_task.done():
        _due_reminder_task.cancel()
        try:
            await _due_reminder_task
        except asyncio.CancelledError:
            pass

    # Stop TTS scheduler
    try:
        from tts_scheduler import get_scheduler
        tts_scheduler = get_scheduler()
        await tts_scheduler.stop()
    except Exception:
        pass
    
    # Stop meter tracking service
    try:
        from meter_service import get_meter_service
        meter_service = get_meter_service()
        await meter_service.stop_polling()
    except Exception:
        pass

class CredentialsModel(BaseModel):
    username: str
    password: Optional[str] = None
    totp_secret: str

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    totp_code: Optional[str] = None

class AppSettingsModel(BaseModel):
    time_offset_hours: float = 0.0
    settings_password: str = "0000"
    auto_download_pdfs: Optional[bool] = None  # None = preserve existing

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(encrypted_data.encode()).decode()

async def save_credentials(username: str, password: str, totp_secret: str):
    """Save encrypted credentials to database"""
    credentials = {
        "username": encrypt_data(username),
        "password": encrypt_data(password),
        "totp_secret": encrypt_data(totp_secret),
        "updated_at": utc_now_iso()
    }
    await db.save_credentials_db(credentials)

async def load_credentials() -> Optional[dict]:
    """Load and decrypt credentials from database"""
    try:
        data = await db.get_credentials_db()
        if not data:
            return None
        
        return {
            "username": decrypt_data(data["username"]),
            "password": decrypt_data(data["password"]),
            "totp_secret": decrypt_data(data["totp_secret"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load credentials: {str(e)}")

# ==========================================
# TTS TRIGGER DETECTION
# ==========================================

async def load_tts_payment_state() -> dict:
    """Load the last known payment state for TTS trigger detection from database"""
    try:
        data = await db.get_tts_payment_state_db()
        if not data:
            return {"bill_id": None, "payment_count": 0, "last_payment_id": None}
        return data
    except Exception as e:
        logging.warning(f"Failed to load TTS payment state: {str(e)}")
        return {"bill_id": None, "payment_count": 0, "last_payment_id": None}

async def save_tts_payment_state(state: dict):
    """Save the TTS payment state to database"""
    try:
        await db.save_tts_payment_state_db(state)
    except Exception as e:
        logging.warning(f"Failed to save TTS payment state: {str(e)}")

async def load_tts_bill_state() -> dict:
    """Load the last known bill state for TTS trigger detection from database"""
    try:
        data = await db.get_tts_bill_state_db()
        if not data:
            return {"latest_bill_id": None, "bill_total": None}
        return data
    except Exception as e:
        logging.warning(f"Failed to load TTS bill state: {str(e)}")
        return {"latest_bill_id": None, "bill_total": None}

async def save_tts_bill_state(state: dict):
    """Save the TTS bill state to database"""
    try:
        await db.save_tts_bill_state_db(state)
    except Exception as e:
        logging.warning(f"Failed to save TTS bill state: {str(e)}")

async def should_trigger_payment_tts() -> tuple:
    """
    Check if we should trigger TTS for a new payment.
    Independent of MQTT - uses its own state file.
    
    Payment data is ALWAYS from the most recent billing cycle only.
    
    Returns (should_trigger: bool, payment_data: dict or None, reason: str)
    
    Triggers when:
    1. New payment added to the most recent bill (payment count increased)
    2. First time seeing a payment (no previous state)
    
    Does NOT trigger for:
    - Payee changes only
    - Bill cycle changes without new payments
    - Reordering existing payments
    """
    current_state = await db.get_most_recent_bill_payment_count()
    previous_state = await load_tts_payment_state()
    
    current_bill_id = current_state.get("bill_id")
    current_count = current_state.get("payment_count", 0)
    
    # Get the latest payment from the MOST RECENT billing cycle only
    latest_payment = current_state.get("last_payment")
    
    previous_bill_id = previous_state.get("bill_id")
    previous_count = previous_state.get("payment_count", 0)
    previous_last_payment_id = previous_state.get("last_payment_id")
    
    # Debug logging
    await db.add_log("debug", f"Payment TTS check: current_bill={current_bill_id}, prev_bill={previous_bill_id}, current_count={current_count}, prev_count={previous_count}")
    
    should_trigger = False
    reason = ""
    
    # No payments at all
    if not latest_payment:
        # Update state but don't trigger
        new_state = {
            "bill_id": current_bill_id,
            "payment_count": 0,
            "last_payment_id": None
        }
        await save_tts_payment_state(new_state)
        return False, None, "No payments found"
    
    current_last_id = latest_payment.get("id")
    
    # Case 1: Same bill, payment count increased = new payment added
    if current_bill_id == previous_bill_id and current_count > previous_count:
        should_trigger = True
        reason = f"New payment added (count: {previous_count} -> {current_count})"
    
    # Case 2: New billing cycle with payments - only trigger if there's a NEW payment
    # (not just carrying over from last scrape)
    elif current_bill_id != previous_bill_id:
        # Only trigger if the latest payment ID is different from what we saw before
        # This means a new payment was actually added, not just a bill cycle change
        if current_last_id != previous_last_payment_id and current_count > 0:
            should_trigger = True
            reason = f"New payment in new billing cycle"
    
    # Case 3: Same bill, same count - no change
    elif current_bill_id == previous_bill_id and current_count == previous_count:
        reason = f"No new payments (count unchanged: {current_count})"
    
    # Update state
    new_state = {
        "bill_id": current_bill_id,
        "payment_count": current_count,
        "last_payment_id": current_last_id
    }
    await save_tts_payment_state(new_state)
    
    if should_trigger:
        await db.add_log("debug", f"Payment TTS WILL trigger: {reason}")
    
    return should_trigger, latest_payment if should_trigger else None, reason

async def should_trigger_new_bill_tts() -> tuple:
    """
    Check if we should trigger TTS for a new bill.
    Independent of MQTT - uses its own state file.
    
    Returns (should_trigger: bool, bill_data: dict or None, reason: str)
    
    Triggers when:
    1. A new bill appears (different bill_id as latest)
    2. First time seeing any bill (no previous state) - SKIP to avoid false positive
    
    Does NOT trigger for:
    - Same bill with updated amounts
    - Payment changes
    """
    # Using db module for database operations
    
    all_bills = await db.get_all_bills()
    previous_state = await load_tts_bill_state()
    
    if not all_bills or len(all_bills) == 0:
        return False, None, "No bills found"
    
    latest_bill = all_bills[0]
    current_bill_id = latest_bill.get("id")
    previous_bill_id = previous_state.get("latest_bill_id")
    
    # Debug logging
    await db.add_log("debug", f"Bill TTS check: current_bill_id={current_bill_id}, prev_bill_id={previous_bill_id}")
    
    should_trigger = False
    reason = ""
    bill_data = None
    
    # Case 1: New bill detected (different ID)
    if previous_bill_id is not None and current_bill_id != previous_bill_id:
        should_trigger = True
        reason = f"New bill detected (ID: {current_bill_id})"
        
        # Get bill details for TTS
        bill_details = await db.get_bill_details(current_bill_id)
        bill_data = {
            "month_range": latest_bill.get("month_range", ""),
            "bill_total": latest_bill.get("bill_total", ""),
            "amount_numeric": latest_bill.get("amount_numeric"),
            "due_date": bill_details.get("due_date", "") if bill_details else "",
        }
        await db.add_log("debug", f"Bill TTS WILL trigger: {reason}")
    
    # Case 2: First time - just initialize state, don't trigger
    # (Avoid announcing existing bills on first run)
    elif previous_bill_id is None:
        reason = "First run - initializing state without triggering"
    else:
        reason = f"Same bill (ID: {current_bill_id})"
    
    # Update state
    new_state = {
        "latest_bill_id": current_bill_id,
        "bill_total": latest_bill.get("bill_total")
    }
    await save_tts_bill_state(new_state)
    
    return should_trigger, bill_data, reason


# Payment verification settings (notification-based claim behavior)
DEFAULT_PAYMENT_VERIFICATION = {
    "notification_claims_enabled": True,
    "auto_send_claims_after_scrape": True,
    "claim_resend_delay_hours": 24,
    "auto_assign_single_non_responder": True,
    "petitions_enabled": True,
}


async def save_app_settings(settings: dict):
    """Save app settings (time offset, password, auto_download_pdfs) to database. Merges with existing."""
    existing = await db.get_app_settings_db() or {}
    settings_data = {
        "time_offset_hours": float(settings.get("time_offset_hours", existing.get("time_offset_hours", 0.0))),
        "settings_password": encrypt_data(settings.get("settings_password", "0000")),
        "updated_at": utc_now_iso()
    }
    if "auto_download_pdfs" in settings:
        settings_data["auto_download_pdfs"] = bool(settings["auto_download_pdfs"])
    else:
        settings_data["auto_download_pdfs"] = existing.get("auto_download_pdfs", True)
    if "breakdown_show_rollover" in settings:
        settings_data["breakdown_show_rollover"] = bool(settings["breakdown_show_rollover"])
    else:
        settings_data["breakdown_show_rollover"] = existing.get("breakdown_show_rollover", False)
    if "claim_resend_delay_hours" in settings:
        settings_data["claim_resend_delay_hours"] = int(settings["claim_resend_delay_hours"])
    else:
        settings_data["claim_resend_delay_hours"] = existing.get("claim_resend_delay_hours", 24)
    # Preserve payment_verification when saving other app settings
    settings_data["payment_verification"] = existing.get("payment_verification") or DEFAULT_PAYMENT_VERIFICATION
    await db.save_app_settings_db(settings_data)

async def load_app_settings() -> dict:
    """Load app settings from database"""
    try:
        data = await db.get_app_settings_db()
        if not data:
            # Create default settings
            default_settings = {
                "time_offset_hours": 0.0,
                "settings_password": "0000",
                "auto_download_pdfs": True,
                "breakdown_show_rollover": False,
                "claim_resend_delay_hours": 24,
            }
            await save_app_settings(default_settings)
            return default_settings
        
        return {
            "time_offset_hours": float(data.get("time_offset_hours", 0.0)),
            "settings_password": decrypt_data(data.get("settings_password", encrypt_data("0000"))) if data.get("settings_password") else "0000",
            "auto_download_pdfs": data.get("auto_download_pdfs", True),
            "breakdown_show_rollover": data.get("breakdown_show_rollover", False),
            "claim_resend_delay_hours": int(data.get("claim_resend_delay_hours", 24)),
        }
    except Exception as e:
        logging.warning(f"Failed to load app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "settings_password": "0000", "auto_download_pdfs": True, "breakdown_show_rollover": False, "claim_resend_delay_hours": 24}

async def verify_settings_password(password: str) -> bool:
    """Verify settings password"""
    settings = await load_app_settings()
    return settings.get("settings_password") == password


async def get_payment_verification_settings() -> dict:
    """Get payment verification config, merged with defaults."""
    data = await db.get_app_settings_db()
    pv = (data or {}).get("payment_verification") or {}
    result = {**DEFAULT_PAYMENT_VERIFICATION, **pv}
    # Backward compat: claim_resend_delay_hours at root
    if "claim_resend_delay_hours" not in pv and data and "claim_resend_delay_hours" in data:
        result["claim_resend_delay_hours"] = int(data.get("claim_resend_delay_hours", 24))
    return result

async def save_payment_verification_settings(updates: dict) -> dict:
    """Save payment verification config (partial merge)."""
    data = await db.get_app_settings_db() or {}
    pv = data.get("payment_verification") or {}
    pv_merged = {**DEFAULT_PAYMENT_VERIFICATION, **pv, **updates}
    pv_merged["claim_resend_delay_hours"] = max(1, min(72, int(pv_merged.get("claim_resend_delay_hours", 24))))
    data["payment_verification"] = pv_merged
    await db.save_app_settings_db(data)
    return pv_merged

# Frontend SPA - path to Vue build output (set by Dockerfile or dev)
_SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = _SCRIPT_DIR.parent / "frontend" / "dist"
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = _SCRIPT_DIR / "frontend" / "dist"

@app.get("/api/totp")
async def get_totp():
    """Get current TOTP code"""
    try:
        credentials = await load_credentials()
        if not credentials:
            raise HTTPException(status_code=404, detail="No credentials found. Please configure settings first.")
        
        # Get TOTP secret and ensure it's a string
        totp_secret = credentials.get("totp_secret", "").strip()
        if not totp_secret:
            raise HTTPException(status_code=400, detail="TOTP secret is empty")
        
        # Create TOTP object
        totp = pyotp.TOTP(totp_secret)
        
        # Generate current code
        current_code = totp.now()
        
        # Calculate time remaining (TOTP codes refresh every 30 seconds)
        current_time = int(time.time())
        time_remaining = 30 - (current_time % 30)
        
        return {
            "code": current_code,
            "time_remaining": time_remaining
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate TOTP: {str(e)}\n{traceback.format_exc()}"
        await db.add_log("error", error_detail)
        raise HTTPException(status_code=500, detail=f"Failed to generate TOTP: {str(e)}")

@app.post("/api/settings")
async def save_settings(credentials: CredentialsModel):
    """Save credentials"""
    try:
        # Validate and normalize TOTP secret
        totp_secret = credentials.totp_secret.strip().upper()
        if not totp_secret:
            raise HTTPException(status_code=400, detail="TOTP secret cannot be empty")
        
        # Validate TOTP secret format by trying to generate a code
        try:
            totp = pyotp.TOTP(totp_secret)
            test_code = totp.now()
            await db.add_log("info", f"TOTP secret validated successfully, test code: {test_code}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid TOTP secret format: {str(e)}")
        
        # If password is not provided, use existing password
        if credentials.password is None or credentials.password == "":
            existing_creds = await load_credentials()
            if existing_creds:
                password = existing_creds["password"]
                await db.add_log("info", "Using existing password")
            else:
                raise HTTPException(status_code=400, detail="Password is required for new credentials")
        else:
            password = credentials.password
        
        # Save credentials
        await save_credentials(
            credentials.username.strip(),
            password,
            totp_secret
        )
        
        await db.add_log("success", "Credentials saved successfully")
        return {"message": "Credentials saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to save settings: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

@app.get("/api/settings")
async def get_settings():
    """Get saved credentials (without sensitive data)"""
    try:
        credentials = await load_credentials()
        if not credentials:
            return {"username": "", "password": "", "totp_secret": ""}
        
        return {
            "username": credentials.get("username", ""),
            "password": "***" * len(credentials.get("password", "")),  # Masked
            "totp_secret": credentials.get("totp_secret", "")
        }
    except Exception as e:
        await db.add_log("error", f"Failed to get settings: {str(e)}")
        return {"username": "", "password": "", "totp_secret": ""}

@app.post("/api/test-login")
async def test_login():
    """Test ConEd login credentials without performing full scrape"""
    from browser_automation import perform_login
    
    credentials = await load_credentials()
    if not credentials:
        raise HTTPException(status_code=404, detail="No credentials found. Please save credentials first.")
    
    await db.add_log("info", "Testing ConEd login credentials...")
    
    username = credentials["username"]
    password = credentials["password"]
    totp = pyotp.TOTP(credentials["totp_secret"])
    totp_code = totp.now()
    
    try:
        result = await perform_login(username, password, totp_code, test_only=True)
        success = result.get('success', False)
        
        if success:
            await db.add_log("success", "Login test successful")
            return {"success": True, "message": "Login successful! Credentials are valid."}
        else:
            error_msg = result.get('error', 'Login failed - could not verify credentials')
            await db.add_log("error", f"Login test failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        await db.add_log("error", f"Login test error: {error_msg}")
        # Most exceptions from browser automation are credential-related
        if any(keyword in error_msg.lower() for keyword in ['login failed', 'error detected', 'incorrect', 'invalid', 'timeout']):
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {error_msg}")

@app.post("/api/scrape")
async def start_scraper():
    """Start scraper automation"""
    import time as time_module
    start_time = time_module.time()
    
    from browser_automation import perform_login
    
    credentials = await load_credentials()
    if not credentials:
        await db.add_scrape_history(False, "No credentials found", "credentials_check", 0)
        raise HTTPException(status_code=404, detail="No credentials found. Please configure settings first.")
    
    # Clear previous logs when starting a new scrape
    await db.clear_logs()
    await db.add_log("info", "Scraper started by user")
    
    # Use saved credentials
    username = credentials["username"]
    password = credentials["password"]
    
    # Generate TOTP code
    totp = pyotp.TOTP(credentials["totp_secret"])
    totp_code = totp.now()
    
    try:
        result = await perform_login(username, password, totp_code)
        success = result.get('success', False)
        scraped_data = result.get('data', {})
        
        if success and scraped_data:
            # ==========================================
            # TTS TRIGGERS AND NOTIFICATIONS
            # ==========================================
            
            # Check for new payment TTS trigger
            try:
                tts_payment_trigger, tts_payment_data, tts_payment_reason = await should_trigger_payment_tts()
                if tts_payment_trigger and tts_payment_data:
                    await db.add_log("info", f"Triggering payment TTS: {tts_payment_reason}")
                    from tts_scheduler import trigger_payment_received_tts
                    payment_amount = tts_payment_data.get("amount", "")
                    current_balance = scraped_data.get("account_balance", "")
                    payee_name = tts_payment_data.get("payee_name", "")
                    await trigger_payment_received_tts(payment_amount, current_balance, payee_name)
                    # Send push notification for payment
                    try:
                        from notifications import notify_payment_received
                        await notify_payment_received(
                            amount=payment_amount,
                            balance=current_balance,
                            payee_name=payee_name
                        )
                    except Exception as notify_e:
                        await db.add_log("warning", f"Failed to send payment notification: {notify_e}")
                else:
                    await db.add_log("debug", f"No payment TTS: {tts_payment_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger payment TTS: {tts_e}")
            
            # Check for new bill TTS trigger
            try:
                tts_bill_trigger, tts_bill_data, tts_bill_reason = await should_trigger_new_bill_tts()
                if tts_bill_trigger and tts_bill_data:
                    await db.add_log("info", f"Triggering new bill TTS: {tts_bill_reason}")
                    from tts_scheduler import trigger_new_bill_tts
                    await trigger_new_bill_tts(
                        bill_month_range=tts_bill_data.get("month_range", ""),
                        bill_total=tts_bill_data.get("bill_total", ""),
                        due_date=tts_bill_data.get("due_date", "")
                    )
                    # Send push notification for new bill
                    try:
                        from notifications import notify_new_bill
                        await notify_new_bill(
                            amount=tts_bill_data.get("bill_total", "N/A"),
                            due_date=tts_bill_data.get("due_date", "N/A"),
                            month_range=tts_bill_data.get("month_range", "N/A")
                        )
                    except Exception as notify_e:
                        await db.add_log("warning", f"Failed to send new bill notification: {notify_e}")
                else:
                    await db.add_log("debug", f"No bill TTS: {tts_bill_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger bill TTS: {tts_e}")
            
        # Due date reminders run at configured time via due_reminder_scheduler_loop
        
        duration = time_module.time() - start_time
        await db.add_scrape_history(success, None if success else "Scrape failed", None, duration)
        await db.add_log("success", f"Scraper completed: {success}")
        return result
    except Exception as e:
        duration = time_module.time() - start_time
        error_msg = str(e)
        await db.add_scrape_history(False, error_msg, "unknown", duration)
        await db.add_log("error", f"Scraper failed: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/app-settings")
async def cleanup_mqtt_sensors():
    """Remove all MQTT discovery messages (clears retained sensors from broker).
    
    Use this to fix duplicate sensor issues - it publishes empty retained messages
    to all discovery topics, which tells Home Assistant to remove those sensors.
    After running this, restart the addon to re-register sensors cleanly.
    """
    try:
        mqtt_config = await load_mqtt_config()
        if not mqtt_config.get("mqtt_url"):
            raise HTTPException(status_code=400, detail="MQTT not configured")
        
        from mqtt_client import init_mqtt_client
        
        client = init_mqtt_client(
            mqtt_url=mqtt_config.get("mqtt_url", ""),
            username=mqtt_config.get("mqtt_username", ""),
            password=mqtt_config.get("mqtt_password", ""),
            base_topic=mqtt_config.get("mqtt_base_topic", "coned"),
            qos=mqtt_config.get("mqtt_qos", 1),
            retain=mqtt_config.get("mqtt_retain", True),
            discovery=mqtt_config.get("mqtt_discovery", True),
        )
        
        if not client:
            raise HTTPException(status_code=500, detail="Failed to create MQTT client")
        
        await client.cleanup_discovery()
        await db.add_log("success", "MQTT discovery cleanup completed - sensors removed from broker")
        return {"message": "MQTT sensors cleared. Restart addon to re-register."}
    except Exception as e:
        error_msg = f"MQTT cleanup failed: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/app-settings")
async def save_app_settings_endpoint(settings: AppSettingsModel):
    """Save app settings (time offset, password)"""
    try:
        settings_dict = {
            "time_offset_hours": settings.time_offset_hours,
            "settings_password": settings.settings_password.strip() if settings.settings_password else "0000",
        }
        await save_app_settings(settings_dict)
        await db.add_log("success", "App settings saved successfully")
        return {"message": "Settings saved successfully"}
    except Exception as e:
        error_msg = f"Failed to save app settings: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/app-settings")
async def get_app_settings_endpoint():
    """Get app settings"""
    try:
        settings = await load_app_settings()
        # Don't return the actual password, just whether one exists
        return {
            "time_offset_hours": settings.get("time_offset_hours", 0.0),
            "has_password": bool(settings.get("settings_password")),
            "settings_password": settings.get("settings_password", "0000"),  # Needed for preservation
            "auto_download_pdfs": settings.get("auto_download_pdfs", True),
            "breakdown_show_rollover": settings.get("breakdown_show_rollover", False),
        }
    except Exception as e:
        await db.add_log("error", f"Failed to get app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "has_password": True, "settings_password": "0000", "auto_download_pdfs": True, "breakdown_show_rollover": False}

class AutoDownloadPdfsModel(BaseModel):
    auto_download_pdfs: bool

class PayeePreferencesModel(BaseModel):
    breakdown_show_rollover: Optional[bool] = None

@app.patch("/api/app-settings")
async def patch_app_settings_endpoint(data: AutoDownloadPdfsModel):
    """Update auto_download_pdfs setting only"""
    try:
        settings = await load_app_settings()
        settings["auto_download_pdfs"] = data.auto_download_pdfs
        await save_app_settings(settings)
        return {"message": "Settings updated", "auto_download_pdfs": data.auto_download_pdfs}
    except Exception as e:
        await db.add_log("error", f"Failed to update app settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/app-settings/payee-preferences")
async def patch_payee_preferences_endpoint(data: PayeePreferencesModel):
    """Update payee-related preferences (breakdown mode, etc.)"""
    try:
        settings = await load_app_settings()
        if data.breakdown_show_rollover is not None:
            settings["breakdown_show_rollover"] = data.breakdown_show_rollover
        await save_app_settings(settings)
        return {"message": "Preferences updated", "breakdown_show_rollover": settings.get("breakdown_show_rollover", False)}
    except Exception as e:
        await db.add_log("error", f"Failed to update payee preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class PaymentVerificationSettingsModel(BaseModel):
    notification_claims_enabled: Optional[bool] = None
    auto_send_claims_after_scrape: Optional[bool] = None
    claim_resend_delay_hours: Optional[int] = None
    auto_assign_single_non_responder: Optional[bool] = None
    petitions_enabled: Optional[bool] = None


@app.get("/api/payment-verification-settings")
async def get_payment_verification_settings_endpoint():
    """Get payment verification config (claim notifications, resend delay, auto-assign, petitions)."""
    try:
        return await get_payment_verification_settings()
    except Exception as e:
        await db.add_log("error", f"Failed to get payment verification settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/payment-verification-settings")
async def patch_payment_verification_settings_endpoint(data: PaymentVerificationSettingsModel):
    """Update payment verification config (partial merge)."""
    try:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            return await get_payment_verification_settings()
        result = await save_payment_verification_settings(updates)
        await db.add_log("info", "Payment verification settings updated")
        return result
    except Exception as e:
        await db.add_log("error", f"Failed to save payment verification settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/automation/install-payment-claim")
async def install_payment_claim_automation():
    """
    Create the payment claim automation package file in HA config.
    Writes to /config/packages/coned_payment_claim.yaml with rest_command + automation.
    User must have 'packages: !include_dir_named packages' in configuration.yaml (or restart HA after adding it).
    """
    import aiohttp
    from pathlib import Path

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="Not running as Home Assistant addon")

    # Get addon slug from Supervisor
    addon_slug = "local_coned_scraper"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://supervisor/addons/self/info",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    addon_slug = info.get("slug") or info.get("data", {}).get("slug") or "local_coned_scraper"
    except Exception as e:
        await db.add_log("warning", f"Could not get addon slug: {e}, using default")
        addon_slug = "local_coned_scraper"

    # Ingress URL - HA calls localhost when automation runs
    base_url = "http://localhost:8123"
    claim_action_url = f"{base_url}/api/coned/ingress/{addon_slug}/api/payments/claim-action"

    # DATA_DIR is /config when running as addon
    packages_dir = DATA_DIR / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    package_path = packages_dir / "coned_payment_claim.yaml"

    package_content = f'''# ConEd Payment Claim - Auto-installed by ConEd addon
# When you tap Yes/No on "Did you make this payment?" notifications,
# this automation records your response so payments get assigned.

rest_command:
  coned_payee_claim:
    method: POST
    url: "{claim_action_url}"
    content_type: "application/json"
    payload_template: '{{{{ "action": "{{{{ action }}}}" }}}}'

automation:
  - id: coned_payment_claim
    alias: ConEd Payment Claim - Record Yes/No
    description: Record payee claim when user taps Yes or No on payment notification
    trigger:
      - platform: event
        event_type:
          - mobile_app_notification_action
          - ios.notification_action
    condition:
      - condition: template
        value_template: >-
          {{{{ trigger.event.data.action is defined
             and trigger.event.data.action.startswith('CONED_CLAIM_') }}}}
    action:
      - service: rest_command.coned_payee_claim
        data:
          action: "{{{{ trigger.event.data.action }}}}"
    mode: single
'''

    try:
        package_path.write_text(package_content, encoding="utf-8")
        await db.add_log("info", f"Installed payment claim automation to {package_path}")

        # Check if configuration.yaml includes packages
        config_path = DATA_DIR / "configuration.yaml"
        packages_included = False
        if config_path.exists():
            config_text = config_path.read_text(encoding="utf-8")
            packages_included = "packages" in config_text.lower() and ("include_dir_named" in config_text or "include_dir" in config_text)

        return {
            "success": True,
            "path": str(package_path),
            "packages_include_needed": not packages_included,
            "message": "Package file created. Restart Home Assistant to load the automation."
            if packages_included
            else "Package file created. Add 'packages: !include_dir_named packages' under 'homeassistant:' in configuration.yaml, then restart Home Assistant.",
        }
    except Exception as e:
        await db.add_log("error", f"Failed to install payment claim automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PasswordVerifyModel(BaseModel):
    password: str

@app.post("/api/app-settings/verify-password")
async def verify_password_endpoint(data: PasswordVerifyModel):
    """Verify settings password"""
    try:
        is_valid = await verify_settings_password(data.password)
        return {"valid": is_valid}
    except Exception as e:
        await db.add_log("error", f"Failed to verify password: {str(e)}")
        return {"valid": False}

class AdminResetPasswordModel(BaseModel):
    user_id: int
    new_password: str

@app.post("/api/app-settings/admin-reset-password")
async def admin_reset_password_endpoint(data: AdminResetPasswordModel):
    """Reset settings password (admin only)"""
    # Using db module for database operations
    
    admin_users = await db.get_admin_users()
    admin_ids = {u['id'] for u in admin_users}
    
    if data.user_id not in admin_ids:
        raise HTTPException(status_code=403, detail="Only admin users can reset the password")
    
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    
    try:
        settings = await load_app_settings()
        settings['settings_password'] = data.new_password
        await save_app_settings(settings)
        await db.add_log("info", f"Settings password reset by admin user {data.user_id}")
        return {"success": True, "message": "Password reset successfully"}
    except Exception as e:
        await db.add_log("error", f"Failed to reset password: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset password")

@app.get("/api/app-settings/admin-users")
async def get_admin_users_endpoint():
    """Get list of admin users"""
    # Using db module for database operations
    return {"admin_users": await db.get_admin_users()}

@app.get("/api/app-settings/check-ha-admin")
async def check_ha_admin(request: Request):
    """Check if current user can reset PIN (running in HA addon mode with supervisor access)"""
    # In HA addon mode, check for supervisor token which means we're running as an addon
    # The HA ingress authentication already ensures only authorized users can access the addon
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    # Also try to get username from ingress headers
    ha_user = request.headers.get("X-Ingress-Path", "")
    
    # If we have a supervisor token, user has addon access = can reset
    # This is secure because HA ingress already authenticates the user
    is_admin = bool(token)
    
    return {"is_admin": is_admin, "username": ha_user or "addon-user"}

class HaAdminResetPasswordModel(BaseModel):
    new_password: str

@app.post("/api/app-settings/ha-admin-reset-password")
async def ha_admin_reset_password(data: HaAdminResetPasswordModel, request: Request):
    """Reset settings password (for authenticated HA addon users)"""
    # In HA addon mode, the supervisor token indicates we're running as an addon
    # HA ingress already authenticates users, so if they can access this endpoint, they're authorized
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    if not token:
        raise HTTPException(status_code=403, detail="PIN reset only available in Home Assistant addon mode")
    
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 characters")
    
    try:
        settings = await load_app_settings()
        settings['settings_password'] = data.new_password
        await save_app_settings(settings)
        await db.add_log("info", "Settings PIN reset via HA addon")
        return {"success": True, "message": "PIN reset successfully"}
    except Exception as e:
        await db.add_log("error", f"Failed to reset PIN: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset PIN")

@app.get("/api/logs")
async def get_logs_endpoint(limit: int = 100):
    """Get log entries"""
    logs = await db.get_logs(limit)
    return {"logs": logs}

@app.delete("/api/logs")
async def clear_logs_endpoint():
    """Clear all log entries"""
    await db.clear_logs()
    return {"message": "Logs cleared successfully"}

@app.get("/api/scrape-history")
async def get_scrape_history_endpoint(limit: int = 50):
    """Get scrape history"""
    history = await db.get_scrape_history(limit)
    return {"history": history}

@app.get("/api/scraped-data")
async def get_scraped_data_endpoint(limit: int = 100):
    """Get scraped data"""
    data = await db.get_all_scraped_data()
    return {"data": data}

@app.get("/api/scraped-data/latest")
async def get_latest_data():
    """Get latest scraped data"""
    data = await db.get_latest_scraped_data(1)
    return {"data": data[0] if data else None}

@app.get("/api/screenshot/{filename}")
async def get_screenshot(filename: str):
    """Get saved screenshot by filename"""
    import os
    from pathlib import Path
    from fastapi.responses import FileResponse, JSONResponse
    
    # Security: prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    
    # Allowed screenshot filenames
    allowed_files = ["account_balance.png", "live_preview.png"]
    if filename not in allowed_files:
        return JSONResponse({"error": "Screenshot not found"}, status_code=404)
    
    # Use DATA_DIR for persistent storage
    screenshot_path = DATA_DIR / filename
    
    if os.path.exists(screenshot_path) and screenshot_path.suffix.lower() == '.png':
        return FileResponse(
            str(screenshot_path),
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        return JSONResponse(
            {"error": "Screenshot not found"},
            status_code=404
        )

def _pdf_response(file_path) -> "Response":
    """Return PDF file as Response with embed headers"""
    from fastapi.responses import Response
    with open(file_path, 'rb') as f:
        pdf_content = f.read()
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Content-Disposition": "inline",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "frame-ancestors 'self' *",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/api/bill-document")
@app.get("/api/bill-document/{bill_id}")
async def get_bill_document_endpoint(bill_id: int = None):
    """Get bill PDF by bill_id, or latest if bill_id omitted"""
    import os
    from fastapi.responses import JSONResponse
    
    if bill_id:
        doc = await db.get_bill_document(bill_id)
        if not doc:
            return JSONResponse({"error": f"No PDF for bill {bill_id}"}, status_code=404)
        pdf_path = DATA_DIR / doc["pdf_path"]
    else:
        latest_id = await db.get_latest_bill_id_with_document()
        if not latest_id:
            return JSONResponse(
                {"error": "No bill PDF available. Add a PDF in Settings → App Settings."},
                status_code=404
            )
        doc = await db.get_bill_document(latest_id)
        pdf_path = DATA_DIR / doc["pdf_path"]
    
    if not os.path.exists(pdf_path):
        return JSONResponse({"error": "PDF file missing"}, status_code=404)
    return _pdf_response(pdf_path)

@app.get("/api/latest-bill-pdf")
async def get_latest_bill_pdf():
    """Get the latest bill PDF (backward compat)"""
    return await get_bill_document_endpoint(bill_id=None)

@app.get("/api/latest-bill-pdf/status")
async def get_pdf_status():
    """Check if any bill PDF exists (for backward compat)"""
    exists = await db.get_latest_bill_id_with_document() is not None
    size = 0
    if exists:
        latest_id = await db.get_latest_bill_id_with_document()
        doc = await db.get_bill_document(latest_id)
        if doc:
            import os
            pdf_path = DATA_DIR / doc["pdf_path"]
            size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
    return {
        "exists": exists,
        "size_bytes": size,
        "size_kb": round(size / 1024, 1) if size else 0,
        "readable": size > 0,
        "path": ""
    }

@app.get("/api/bills/{bill_id}/pdf/status")
async def get_bill_pdf_status(bill_id: int):
    """Check if a specific bill has a PDF"""
    import os
    doc = await db.get_bill_document(bill_id)
    if not doc:
        return {"exists": False, "size_bytes": 0, "size_kb": 0}
    pdf_path = DATA_DIR / doc["pdf_path"]
    exists = os.path.exists(pdf_path)
    size = os.path.getsize(pdf_path) if exists else 0
    return {
        "exists": exists,
        "size_bytes": size,
        "size_kb": round(size / 1024, 1) if size else 0,
    }

class PdfDownloadRequest(BaseModel):
    url: str

async def _download_and_store_pdf(pdf_url: str, bill_id: int) -> dict:
    """Download PDF from URL and store for bill_id. Delegates to pdf_utils."""
    from pdf_utils import download_and_store_pdf
    try:
        return await download_and_store_pdf(pdf_url, bill_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

@app.post("/api/bills/{bill_id}/pdf/download")
async def download_bill_pdf_for_period(bill_id: int, request: PdfDownloadRequest):
    """Download PDF for a specific billing period"""
    bill = await db.get_bill_by_id(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    pdf_url = request.url.strip()
    if not pdf_url:
        raise HTTPException(status_code=400, detail="PDF URL is required")
    result = await _download_and_store_pdf(pdf_url, bill_id)
    return result

@app.post("/api/latest-bill-pdf/download")
async def download_bill_pdf(request: PdfDownloadRequest):
    """Download PDF for the latest bill (backward compat - uses most recent bill in DB)"""
    pdf_url = request.url.strip()
    if not pdf_url:
        raise HTTPException(status_code=400, detail="PDF URL is required")
    bills = await db.get_all_bills()
    if not bills:
        raise HTTPException(status_code=400, detail="No bills in ledger. Run scraper first.")
    bill_id = bills[0]['id']
    result = await _download_and_store_pdf(pdf_url, bill_id)
    return result


@app.delete("/api/latest-bill-pdf")
async def delete_latest_bill_pdf():
    """Delete the latest bill PDF"""
    latest_id = await db.get_latest_bill_id_with_document()
    if not latest_id:
        return {"success": True, "message": "No PDF to delete"}
    return await _delete_bill_pdf_by_id(latest_id)

@app.delete("/api/bills/{bill_id}/pdf")
async def delete_bill_pdf_by_id(bill_id: int):
    """Delete a specific bill's PDF"""
    return await _delete_bill_pdf_by_id(bill_id)

async def _delete_bill_pdf_by_id(bill_id: int):
    import os
    doc = await db.get_bill_document(bill_id)
    if not doc:
        return {"success": True, "message": "No PDF to delete"}
    pdf_path = DATA_DIR / doc["pdf_path"]
    await db.delete_bill_document(bill_id)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        await db.add_log("info", "Bill PDF deleted")
    
    # Also delete parsed bill details
    await db.delete_bill_details(bill_id)
    
    return {"success": True, "message": "PDF deleted"}


# ========== Bill Details & History API ==========

@app.get("/api/bills/{bill_id}/details")
async def get_bill_details_endpoint(bill_id: int):
    """Get parsed bill details for a specific bill"""
    # Using db module for database operations
    details = await db.get_bill_details(bill_id)
    if not details:
        raise HTTPException(status_code=404, detail="Bill details not found. Upload PDF first.")
    return details

@app.post("/api/bills/{bill_id}/parse-pdf")
async def parse_bill_pdf_endpoint(bill_id: int):
    """Re-parse an existing bill PDF"""
    # Using db module for database operations
    from pdf_parser import parse_coned_bill_pdf
    
    doc = await db.get_bill_document(bill_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No PDF found for this bill")
    
    pdf_path = DATA_DIR / doc["pdf_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file missing")
    
    parsed_data = parse_coned_bill_pdf(str(pdf_path))
    if "error" in parsed_data:
        raise HTTPException(status_code=500, detail=parsed_data["error"])
    
    await db.upsert_bill_details(bill_id, **parsed_data)
    await db.add_log("info", f"Re-parsed bill {bill_id}: kWh={parsed_data.get('kwh_used')}")
    return {"success": True, "details": parsed_data}

@app.get("/api/bill-history")
async def get_bill_history_endpoint():
    """Get bill history data for graphing"""
    # Using db module for database operations
    history = await db.get_bill_history_for_graph()
    return {"history": history}

@app.get("/api/bill-details/all")
async def get_all_bill_details_endpoint():
    """Get all bill details"""
    # Using db module for database operations
    details = await db.get_all_bill_details()
    return {"details": details}

@app.get("/api/bill-details/latest")
async def get_latest_bill_details_endpoint():
    """Get the latest bill with its details (for sensors)"""
    # Using db module for database operations
    latest = await db.get_latest_bill_with_details()
    if not latest:
        return {"bill": None, "due_date": None, "kwh_cost": None}
    return {
        "bill": latest,
        "due_date": latest.get("due_date"),
        "kwh_cost": latest.get("kwh_cost"),
        "kwh_used": latest.get("kwh_used")
    }

@app.post("/api/bill-details/reparse-all")
async def reparse_all_bill_pdfs():
    """Re-parse all existing bill PDFs to extract/update bill details"""
    # Using db module for database operations
    from pdf_parser import parse_coned_bill_pdf
    
    docs = await db.get_all_bill_documents_with_periods()
    results = {"success": 0, "failed": 0, "errors": []}
    
    for doc in docs:
        bill_id = doc["bill_id"]
        pdf_path = DATA_DIR / doc["pdf_path"]
        
        if not os.path.exists(pdf_path):
            results["failed"] += 1
            results["errors"].append(f"Bill {bill_id}: PDF file missing")
            continue
        
        try:
            parsed_data = parse_coned_bill_pdf(str(pdf_path))
            if "error" in parsed_data:
                results["failed"] += 1
                results["errors"].append(f"Bill {bill_id}: {parsed_data['error']}")
            else:
                # Only pass keys that upsert_bill_details accepts (parser may include extras like parsed_at)
                detail_keys = (
                    "due_date", "kwh_used", "kwh_cost", "electricity_total",
                    "total_from_billing_period", "balance_from_previous_bill", "total_amount_due",
                    "billing_days", "supply_charges", "delivery_charges",
                    "billing_period_start", "billing_period_end",
                )
                kwargs = {k: v for k, v in parsed_data.items() if k in detail_keys}
                await db.upsert_bill_details(bill_id, **kwargs)
                results["success"] += 1
                await db.add_log("info", f"Re-parsed bill {bill_id}: kWh={parsed_data.get('kwh_used')}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Bill {bill_id}: {str(e)}")
    
    return {
        "success": True,
        "message": f"Parsed {results['success']} bills, {results['failed']} failed",
        "details": results
    }


@app.get("/api/live-preview")
async def get_live_preview():
    """Get the latest live preview screenshot"""
    import os
    from pathlib import Path
    from fastapi.responses import FileResponse, JSONResponse
    
    screenshot_path = DATA_DIR / "live_preview.png"
    
    if os.path.exists(screenshot_path):
        return FileResponse(
            str(screenshot_path),
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        # Return a placeholder or 404
        return JSONResponse(
            {"error": "Live preview not available"},
            status_code=404
        )

@app.get("/api/automated-schedule")
async def get_automated_schedule():
    """Get automated scraping schedule"""
    global _scrape_running
    schedule = await load_schedule()
    
    # Check if a scrape is currently running
    if _scrape_running:
        return {
            "enabled": schedule["enabled"],
            "frequency": schedule["frequency"],
            "nextRun": None,
            "isRunning": True,
            "lastScrapeEnd": schedule.get("last_scrape_end")
        }
    
    # Use the stored next_run time (calculated from last_scrape_end + frequency)
    next_run = schedule.get("next_run")
    now = datetime.now(timezone.utc)
    
    # If no next_run is set but enabled, calculate from now (first run)
    if schedule["enabled"] and not next_run:
        next_run = (now + timedelta(seconds=schedule["frequency"])).isoformat()
    
    # If next_run is in the past, it means the scheduler will run soon
    if schedule["enabled"] and next_run:
        try:
            next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
            if next_run_dt < now:
                # Scheduler should run imminently
                next_run = (now + timedelta(seconds=5)).isoformat()
        except:
            pass
    
    return {
        "enabled": schedule["enabled"],
        "frequency": schedule["frequency"],
        "nextRun": next_run,
        "isRunning": False,
        "lastScrapeEnd": schedule.get("last_scrape_end")
    }

@app.post("/api/automated-schedule")
async def save_automated_schedule(schedule: ScheduleModel):
    """Save automated scraping schedule"""
    try:
        if schedule.frequency <= 0:
            raise HTTPException(status_code=400, detail="Frequency must be greater than 0")
        
        # Load existing schedule to get last_scrape_end
        existing = await load_schedule()
        last_scrape_end = existing.get("last_scrape_end")
        
        # Calculate next_run based on last_scrape_end + new frequency
        next_run = None
        if schedule.enabled:
            if last_scrape_end:
                try:
                    last_end = datetime.fromisoformat(last_scrape_end.replace('Z', '+00:00'))
                    next_run = (last_end + timedelta(seconds=schedule.frequency)).isoformat()
                except:
                    next_run = (datetime.now(timezone.utc) + timedelta(seconds=schedule.frequency)).isoformat()
            else:
                # No previous scrape, run based on now
                next_run = (datetime.now(timezone.utc) + timedelta(seconds=schedule.frequency)).isoformat()
        
        await save_schedule(schedule.enabled, schedule.frequency, last_scrape_end, next_run)
        
        # Restart scheduler with new settings
        await restart_scheduler()
        
        return {
            "enabled": schedule.enabled,
            "frequency": schedule.frequency,
            "nextRun": next_run,
            "lastScrapeEnd": last_scrape_end,
            "message": "Schedule saved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to save schedule: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# ==========================================
# LEDGER API ENDPOINTS (Database-driven)
# ==========================================

@app.get("/api/ledger")
async def get_ledger():
    """Get complete ledger data from normalized database tables"""
    try:
        data = await db.get_ledger_data()
        return data
    except Exception as e:
        await db.add_log("error", f"Failed to get ledger: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills")
async def get_bills(limit: int = 50):
    """Get all bills from database"""
    try:
        bills = await db.get_all_bills()
        return {"bills": bills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments")
async def get_payments(limit: int = 100, bill_id: Optional[int] = None):
    """Get all payments from database"""
    try:
        payments = await db.get_all_payments(bill_id)
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments/unverified")
async def get_payments_unverified(limit: int = 50):
    """Get payments that need payee verification (unverified or needs_admin_verification)"""
    try:
        payments = await db.get_unverified_payments()
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PayeeClaimModel(BaseModel):
    payee_id: int
    claimed: bool


class PetitionModel(BaseModel):
    payee_id: int


class ClaimActionModel(BaseModel):
    action: str


@app.post("/api/payments/claim-action")
async def record_payee_claim_by_action(body: ClaimActionModel):
    """
    Record a payee's Yes/No response by passing the raw action string.
    Simpler for automations: no need to parse, just forward trigger.event.data.action.

    Action format: CONED_CLAIM_YES_<payment_id>_<payee_id> or CONED_CLAIM_NO_<payment_id>_<payee_id>
    """
    action = (body.action or "").strip()
    if not action.startswith("CONED_CLAIM_"):
        raise HTTPException(status_code=400, detail="Invalid action format")
    parts = action.split("_")
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail="Invalid action format")
    try:
        payment_id = int(parts[3])
        payee_id = int(parts[4])
        claimed = parts[2].upper() == "YES"
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid action format")
    return await record_payee_claim(payment_id, PayeeClaimModel(payee_id=payee_id, claimed=claimed))


@app.post("/api/payments/{payment_id}/payee-claim")
async def record_payee_claim(payment_id: int, body: PayeeClaimModel):
    """
    Record a payee's Yes/No response to a payment claim.
    Called by Home Assistant automation when user taps Yes/No on notification.
    Runs assignment resolution logic after recording.
    """
    try:
        payment = await db.get_payment_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.get("payee_status") not in ("unverified", "needs_admin_verification"):
            raise HTTPException(status_code=400, detail="Payment already assigned")
        result = await db.record_payment_claim_response(payment_id, body.payee_id, body.claimed)
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail="Failed to record claim response")
        # If payee claimed and was assigned, send notification + TTS to all users
        assignment = result.get("assignment")
        if assignment:
            try:
                from notifications import notify_payment_claimed
                from tts_scheduler import trigger_payment_claimed_tts
                await notify_payment_claimed(
                    payee_name=assignment.get("payee_name", "Unknown"),
                    amount=assignment.get("amount", "N/A"),
                    payment_date=assignment.get("payment_date", "N/A"),
                )
                await trigger_payment_claimed_tts(
                    payee_name=assignment.get("payee_name", "Unknown"),
                    amount=assignment.get("amount", "N/A"),
                    payment_date=assignment.get("payment_date", "N/A"),
                )
            except Exception as e:
                await db.add_log("warning", f"Payment claimed notification/TTS failed: {e}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/payments/{payment_id}/petition")
async def create_payment_petition(payment_id: int, body: PetitionModel):
    """Record a petition - payee claiming a payment already assigned to someone else."""
    try:
        pv = await get_payment_verification_settings()
        if not pv.get("petitions_enabled", True):
            raise HTTPException(status_code=400, detail="Petitions are disabled")
        ok = await db.create_payment_petition(payment_id, body.payee_id)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to create petition")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# PAYEE USER MANAGEMENT
# ==========================================

class PayeeUserModel(BaseModel):
    name: str
    ha_user_id: Optional[str] = None
    notify_service: Optional[str] = None
    notifications_enabled: bool = True
    is_default: bool = False

class PayeeUserUpdateModel(BaseModel):
    name: Optional[str] = None
    ha_user_id: Optional[str] = None
    notify_service: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    is_admin: Optional[bool] = None

class PaymentAttributionModel(BaseModel):
    payment_id: int
    user_id: int
    method: str = "manual"

@app.get("/api/payee-users")
async def list_payee_users():
    """Get all payee users"""
    try:
        users = await db.get_payee_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payee-users")
async def create_user(user: PayeeUserModel):
    """Create a new payee user"""
    try:
        new_user = await db.create_payee_user_with_ha(
            name=user.name,
            ha_user_id=user.ha_user_id,
            notify_service=user.notify_service,
            notifications_enabled=user.notifications_enabled,
            is_default=user.is_default
        )
        await db.add_log("info", f"Created payee user: {user.name}")
        return new_user
    except Exception as e:
        if "UNIQUE constraint" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail="User with this name already exists")
        raise HTTPException(status_code=500, detail=str(e))

# NOTE: Specific routes must come BEFORE parameterized routes to avoid route conflicts
@app.put("/api/payee-users/responsibilities")
async def update_responsibilities(request: Request):
    """Update bill responsibility percentages for payees (must total 100%)"""
    try:
        # Bypass Pydantic entirely - parse raw JSON
        body = await request.json()
        await db.add_log("info", f"Received responsibilities request: {body}")
        raw_responsibilities = body.get('responsibilities', {})
        
        # Convert string keys to int, handle various value types
        responsibilities = {}
        for k, v in raw_responsibilities.items():
            try:
                user_id = int(k)
                percent = float(v) if v is not None else 0.0
                responsibilities[user_id] = percent
            except (ValueError, TypeError) as conv_err:
                raise HTTPException(status_code=400, detail=f"Invalid data for user {k}: {v} - {conv_err}")
        
        result = await db.update_payee_responsibilities(responsibilities)
        if result:
            result = {"total": sum(responsibilities.values()), "success": True}
        else:
            result = {"total": 0, "success": False}
        if result['success']:
            await db.add_log("info", f"Updated payee responsibilities: {result['total']}% total")
            return result
        raise HTTPException(status_code=400, detail=result.get('error', 'Invalid percentages'))
    except HTTPException:
        raise
    except Exception as e:
        await db.add_log("error", f"Failed to update responsibilities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/payee-users/{user_id}")
async def update_user(user_id: int, user: PayeeUserUpdateModel):
    """Update a payee user"""
    try:
        # Update basic fields
        if user.name is not None or user.is_default is not None or user.is_admin is not None:
            await db.update_payee_user(user_id, user.name, user.is_default, user.is_admin)
        
        # Update notification fields
        if user.ha_user_id is not None or user.notify_service is not None or user.notifications_enabled is not None:
            await db.update_payee_notify_settings(
                user_id,
                ha_user_id=user.ha_user_id,
                notify_service=user.notify_service,
                notifications_enabled=user.notifications_enabled
            )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/payee-users/{user_id}")
async def delete_user(user_id: int):
    """Delete a payee user"""
    try:
        deleted = await db.delete_payee_user(user_id)
        if deleted:
            await db.add_log("info", f"Deleted payee user ID: {user_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills/all-summaries")
async def get_all_bill_summaries():
    """Get payee summaries for ALL bills at once (efficient - single pass calculation)"""
    try:
        await db.add_log("info", "Calculating all bill summaries...")
        summaries = await db.calculate_all_payee_balances()
        await db.add_log("info", f"Calculated summaries for {len(summaries)} bills")
        return {"summaries": summaries}
    except Exception as e:
        await db.add_log("error", f"Failed to calculate summaries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills/{bill_id}/summary")
async def get_bill_summary(bill_id: int):
    """Get payee payment summary for a specific bill"""
    try:
        summary = await db.get_bill_payee_summary(bill_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/attribute")
async def attribute_payment_to_user(attribution: PaymentAttributionModel):
    """Attribute a payment to a user"""
    try:
        success = await db.attribute_payment(
            attribution.payment_id,
            attribution.user_id,
            payee_status="verified",
            verification_method=attribution.method
        )
        if success:
            await db.add_log("info", f"Attributed payment {attribution.payment_id} to user {attribution.user_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/payments/{payment_id}/attribution")
async def clear_payment_attribution_endpoint(payment_id: int):
    """Clear payment attribution (unassign from user). Used by admin via Settings. Resends payment claim notifications."""
    try:
        payment = await db.get_payment_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        success = await db.clear_payment_attribution(payment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Payment not found")
        await db.add_log("info", f"Cleared attribution for payment {payment_id}")
        # Resend payment claim notifications (like post-scrape) - no TTS
        try:
            await db.reset_claim_responses_for_resend(payment_id)
            from notifications import send_payment_claim_request
            payees = await db.get_payees_with_notifications()
            payment_for_claim = {
                "id": payment_id,
                "amount": payment.get("amount", "N/A"),
                "payment_date": payment.get("payment_date", "N/A"),
                "amount_numeric": payment.get("amount_numeric", 0),
                "description": payment.get("description"),
                "bill_id": payment.get("bill_id"),
            }
            sent = await send_payment_claim_request(payment_for_claim, payees)
            if sent > 0:
                await db.add_log("info", f"Resent payment claim request for payment {payment_id}")
        except Exception as claim_e:
            await db.add_log("warning", f"Resend claim after admin unassign failed: {claim_e}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/payments/{payment_id}/unclaim")
async def unclaim_payment_endpoint(payment_id: int):
    """Unclaim a payment via Account Ledger. Clears attribution and sends TTS + notification (not used for admin Settings unassign)."""
    try:
        payment = await db.get_payment_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        payee_user_id = payment.get("payee_user_id")
        if not payee_user_id:
            raise HTTPException(status_code=400, detail="Payment is not assigned")
        payee_name = payment.get("payee_name") or "Unknown"
        amount = payment.get("amount", "N/A")
        payment_date = payment.get("payment_date", "N/A")
        success = await db.clear_payment_attribution(payment_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to unclaim")
        await db.add_log("info", f"Payment {payment_id} unclaimed via Account Ledger")
        try:
            from notifications import notify_payment_unclaimed
            from tts_scheduler import trigger_payment_unclaimed_tts
            await notify_payment_unclaimed(payee_name=payee_name, amount=amount, payment_date=payment_date)
            await trigger_payment_unclaimed_tts(payee_name=payee_name, amount=amount, payment_date=payment_date)
        except Exception as e:
            await db.add_log("warning", f"Payment unclaimed notification/TTS failed: {e}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/payments/{payment_id}")
async def get_payment_endpoint(payment_id: int):
    """Get a single payment by ID"""
    try:
        payment = await db.get_payment_by_id(payment_id)
        if payment:
            return {"payment": payment}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdatePaymentBillModel(BaseModel):
    bill_id: Optional[int] = None

@app.put("/api/payments/{payment_id}/bill")
async def update_payment_bill_endpoint(payment_id: int, data: UpdatePaymentBillModel):
    """Update which bill a payment belongs to (manual override)"""
    try:
        success = await db.update_payment_bill(payment_id, data.bill_id, manually_set=True)
        if success:
            await db.add_log("info", f"Manually assigned payment {payment_id} to bill {data.bill_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/data/wipe")
async def wipe_all_data():
    """Wipe all bills and payments from database"""
    try:
        result = await db.wipe_bills_and_payments()
        await db.add_log("warning", f"Database wiped: {result['bills_deleted']} bills, {result['payments_deleted']} payments deleted")
        return {"success": True, "status": "success", "message": "Database wiped", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bills/relink-payments")
async def relink_payments_endpoint():
    """Relink orphan payments to bills by date logic (bill_date <= payment_date < next_bill_date)"""
    try:
        updated = await db.relink_payments_to_bills()
        await db.add_log("info", f"Relinked {updated} payments to bills by date")
        return {"success": True, "updated": updated, "message": f"Linked {updated} payments to bills"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdatePaymentOrderModel(BaseModel):
    bill_id: Optional[int] = None
    order: int

@app.put("/api/payments/{payment_id}/order")
async def update_payment_order_endpoint(payment_id: int, data: UpdatePaymentOrderModel):
    """Update payment's bill assignment and order position (manual audit)"""
    try:
        success = await db.update_payment_order(payment_id, data.bill_id, data.order)
        if success:
            await db.add_log("info", f"Manually set payment {payment_id} to bill {data.bill_id} at position {data.order}")
            
            # Check if this manual audit changed the last payment and publish to MQTT
            try:
                from mqtt_client import get_mqtt_client
                mqtt_client = get_mqtt_client()
                if mqtt_client:
                    should_pub, last_payment, reason = await should_publish_last_payment()
                    if should_pub and last_payment:
                        await db.add_log("info", f"Manual audit triggered MQTT publish: {reason}")
                        await mqtt_client.publish_last_payment(last_payment, utc_now_iso())
            except Exception as mqtt_e:
                await db.add_log("warning", f"Failed to publish MQTT after manual audit: {mqtt_e}")
            
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/payments/{payment_id}/manual-audit")
async def clear_payment_manual_audit_endpoint(payment_id: int):
    """Clear/release the manual audit on a payment, allowing auto-logic to take over again"""
    try:
        success = await db.clear_payment_manual_audit()
        if success:
            await db.add_log("info", f"Cleared manual audit for payment {payment_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments/recent-bill-stats")
async def get_recent_bill_payment_stats():
    """Get payment count and last payment for the most recent billing cycle"""
    try:
        stats = await db.get_most_recent_bill_payment_count()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payee-users/{user_id}/payments")
async def get_user_payments(user_id: int):
    """Get all payments assigned to a specific user"""
    try:
        payments = await db.get_payments_by_user(user_id)
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills-with-payments")
async def get_bills_with_payments_endpoint():
    """Get all bills with their payments for the audit tab"""
    try:
        data = await db.get_all_bills_with_payments()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== Meter Tracking Configuration ==========

class MeterConfigModel(BaseModel):
    enabled: bool = False
    email: str = ""
    password: Optional[str] = None
    totp_secret: str = ""
    polling_interval: int = 15


@app.get("/api/meter-config")
async def get_meter_config():
    """Get meter tracking configuration (password masked)"""
    
    config = await db.get_meter_config_db()
    
    # If no meter config exists, try to pre-populate from main credentials
    if not config:
        main_creds = await load_credentials()
        config = {
            "enabled": False,
            "email": main_creds.get('username', '') if main_creds else "",
            "password": "••••••••" if main_creds and main_creds.get('password') else "",
            "totp_secret": main_creds.get('totp_secret', '') if main_creds else "",
            "polling_interval": 15,
            "uses_main_credentials": True
        }
    else:
        if config.get('password'):
            config['password'] = '••••••••'
    
    return config


# Minimum polling interval = quarter-hour data resolution (Con Edison updates every 15 min)
METER_MIN_POLLING_INTERVAL = 15


@app.post("/api/meter-config")
async def save_meter_config_endpoint(config: MeterConfigModel):
    """Save meter tracking configuration"""
    from meter_service import get_meter_service
    
    if config.polling_interval < METER_MIN_POLLING_INTERVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Polling interval cannot be less than {METER_MIN_POLLING_INTERVAL} minutes (data update threshold for quarter-hour readings)"
        )
    
    # Load existing config to preserve password if not provided
    existing = await db.get_meter_config_db() or {}
    
    # Fall back to main credentials if meter-specific fields are empty
    main_creds = await load_credentials()
    
    email = config.email.strip()
    totp_secret = config.totp_secret.strip()
    
    # Use main credentials as fallback
    if not email and main_creds:
        email = main_creds.get('username', '')
    if not totp_secret and main_creds:
        totp_secret = main_creds.get('totp_secret', '')
    
    new_config = {
        "enabled": config.enabled,
        "email": email,
        "totp_secret": totp_secret,
        "polling_interval": config.polling_interval,
        "updated_at": utc_now_iso()
    }
    
    # Handle password - keep existing if masked or empty, or use main credentials
    if config.password and config.password != '••••••••':
        new_config['password'] = encrypt_data(config.password)
    elif existing.get('password'):
        new_config['password'] = existing['password']
    elif main_creds and main_creds.get('password'):
        new_config['password'] = encrypt_data(main_creds['password'])
    else:
        new_config['password'] = ''
    
    await db.save_meter_config_db(new_config)
    
    # Reinitialize meter service with new config
    service = get_meter_service()
    await service.stop_polling()
    
    if new_config['enabled']:
        # Decrypt password for initialization and mark as plain
        init_config = new_config.copy()
        if init_config.get('password'):
            try:
                init_config['password'] = 'plain:' + decrypt_data(init_config['password'])
            except:
                pass
        
        success = await service.initialize(init_config)
        if success:
            await service.start_polling(new_config['polling_interval'])
    
    await db.add_log("info", f"Meter config saved (enabled={new_config['enabled']})")
    return {"success": True, "message": "Meter configuration saved"}


@app.post("/api/meter-config/test")
async def test_meter_connection():
    """Test meter connection by fetching account info and a reading"""
    from meter_service import get_meter_service

    config = await db.get_meter_config_db()
    
    # Fall back to main credentials if no meter config
    if not config or not config.get('email'):
        main_creds = await load_credentials()
        if not main_creds:
            raise HTTPException(status_code=400, detail="No credentials found. Please save credentials first.")
        
        # Password from load_credentials() is already decrypted, mark as plain
        config = {
            'email': main_creds.get('username', ''),
            'password': 'plain:' + main_creds.get('password', ''),
            'totp_secret': main_creds.get('totp_secret', ''),
            'enabled': True,
            'polling_interval': 15
        }
    else:
        # Decrypt password from database and mark as plain
        if config.get('password'):
            try:
                decrypted = decrypt_data(config['password'])
                config['password'] = 'plain:' + decrypted
            except:
                raise HTTPException(status_code=400, detail="Failed to decrypt password")

    service = get_meter_service()
    
    try:
        success = await service.initialize(config)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to initialize meter connection. Check your credentials.")

        # Get account info first (includes smart meter status)
        account_info = await service.get_account_info()
        
        if not account_info:
            raise HTTPException(status_code=400, detail="Login failed. Check your username, password, and TOTP secret.")
        
        # Get forecast
        forecast = await service.fetch_forecast()
        
        # Get latest reading
        reading = await service.fetch_reading()

        if reading:
            return {
                "success": True,
                "message": f"Connected! Latest reading: {reading['value']} {reading['unit']} (from {reading.get('end_time', 'unknown')})",
                "reading": reading,
                "account_info": account_info,
                "forecast": forecast,
                "smart_meter_info": {
                    "has_realtime": account_info.get('has_realtime_access', False) if account_info else False,
                    "resolution": account_info.get('read_resolution') if account_info else None,
                    "note": "Realtime data requires special smart meter enrollment with Con Edison. This addon uses hourly historical data (typically 1-24 hour delay)."
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Connected to account but no meter readings available. Data may be delayed 1-24 hours.")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "password" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"Authentication failed: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Meter test failed: {error_msg}")


@app.get("/api/meter-reading")
async def get_meter_reading():
    """Get latest meter reading with forecast data - uses cached data for immediate load"""
    from meter_service import get_meter_service
    
    service = get_meter_service()
    reading = await service.get_cached_reading()
    
    # Get cached forecast for immediate load (no network call)
    forecast = await service.get_cached_forecast() if service.is_enabled() else None
    
    # Calculate cost using kwh_cost from latest bill
    cost = None
    usage_to_date_cost = None
    latest_bill = await db.get_latest_bill_with_details()
    kwh_cost = latest_bill.get('kwh_cost') if latest_bill else None
    
    if kwh_cost and reading and reading.get('value'):
        cost = reading['value'] * float(kwh_cost)
    
    # Calculate usage_to_date cost from forecast
    if kwh_cost and forecast and forecast.get('usage_to_date'):
        usage_to_date_cost = forecast['usage_to_date'] * float(kwh_cost)
    
    return {
        "enabled": service.is_enabled(),
        "reading": reading,
        "cost": cost,
        "kwh_cost": kwh_cost,
        "forecast": forecast,
        "usage_to_date_cost": usage_to_date_cost
    }


@app.post("/api/meter-reading/refresh")
async def refresh_meter_reading():
    """Force refresh meter reading"""
    from meter_service import get_meter_service
    # Using db module for database operations
    
    service = get_meter_service()
    
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Meter tracking is not enabled")
    
    reading = await service.fetch_reading()
    
    if not reading:
        raise HTTPException(status_code=500, detail="Failed to fetch meter reading")
    
    # Calculate cost
    cost = None
    latest_bill = await db.get_latest_bill_with_details()
    if latest_bill and latest_bill.get('kwh_cost') and reading.get('value'):
        kwh_cost = float(latest_bill['kwh_cost'])
        cost = reading['value'] * kwh_cost
    
    return {
        "success": True,
        "reading": reading,
        "cost": cost
    }


@app.get("/api/meter-reading/realtime")
async def get_realtime_usage(day_offset: int = 0, refresh: bool = False):
    """Get hourly/quarter-hour usage for a specific day. API is delayed, so we show prior days.
    
    Args:
        day_offset: 0 = most recent complete day, 1 = day before, etc.
        refresh: If True, fetch fresh data from API and merge into DB.
    
    Returns:
        readings for that day (full 24h), total_available_days, day_label
    """
    from meter_service import get_meter_service
    
    service = get_meter_service()
    
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Meter tracking is not enabled")
    
    # Optionally fetch fresh data and merge (append) into DB (chunked: API ~6 days/request)
    if refresh:
        await service.fetch_quarter_hour_reads(720)  # 30 days in 6-day chunks
    
    # Get readings for the requested day
    readings, total_days = await db.get_realtime_readings_for_day(day_offset)
    
    # Build day label for display
    day_label = None
    if readings:
        from datetime import datetime, timezone
        first_end = readings[0].get("end_time") if isinstance(readings[0], dict) else None
        if first_end:
            try:
                dt = datetime.fromisoformat(first_end.replace("Z", "+00:00"))
                day_label = dt.strftime("%b %d, %Y")
            except (ValueError, TypeError):
                pass
    
    return {
        "success": True,
        "readings": readings,
        "day_offset": day_offset,
        "total_available_days": total_days,
        "day_label": day_label,
        "count": len(readings),
        "cached": not refresh
    }


# ========== TTS Configuration ==========
async def load_tts_config() -> dict:
    """Load TTS configuration from database (persists across reinstalls)"""
    # Using db module for database operations
    
    # Try database first
    data = await db.get_tts_config_db()
    
    # Migrate from JSON file if database is empty but file exists
    if data is None and TTS_CONFIG_FILE.exists():
        try:
            data = json.loads(TTS_CONFIG_FILE.read_text())
            await db.save_tts_config_db(data)
            await db.add_log("info", "Migrated TTS config from JSON to database")
        except:
            pass
    
    if data is None:
        await save_tts_config(DEFAULT_TTS_CONFIG.copy())
        return DEFAULT_TTS_CONFIG.copy()
    
    try:
        merged = DEFAULT_TTS_CONFIG.copy()
        merged.update(data)
        merged.setdefault("tts_service", "tts.google_translate_say")
        if "messages" not in data or not data["messages"]:
            merged["messages"] = DEFAULT_TTS_CONFIG["messages"].copy()
        else:
            for k, v in DEFAULT_TTS_CONFIG["messages"].items():
                merged["messages"].setdefault(k, v)
            merged["messages"].pop("scrape_complete", None)
            merged["messages"].pop("balance_alert", None)
        return merged
    except Exception as e:
        logging.warning(f"Failed to load TTS config: {str(e)}")
        return DEFAULT_TTS_CONFIG.copy()


async def save_tts_config(config: dict):
    """Save TTS configuration to database"""
    await db.save_tts_config_db(config)


class TTSConfigModel(BaseModel):
    enabled: Optional[bool] = None
    media_player: Optional[str] = None
    volume: Optional[float] = None
    language: Optional[str] = None
    prefix: Optional[str] = None
    wait_for_idle: Optional[bool] = None
    tts_service: Optional[str] = None
    messages: Optional[dict] = None


@app.get("/api/tts-config")
async def get_tts_config():
    """Get TTS configuration"""
    return await load_tts_config()


@app.post("/api/tts-config")
async def save_tts_config_endpoint(config: TTSConfigModel):
    """Save TTS configuration"""
    current = await load_tts_config()
    updates = config.model_dump(exclude_none=True)
    for k, v in updates.items():
        current[k] = v
    await save_tts_config(current)
    return {"success": True}


def build_tts_message(config: dict, key: str, **kwargs) -> str:
    """Build TTS message: (prefix), (message)"""
    prefix = config.get("prefix", DEFAULT_TTS_PREFIX)
    template = config.get("messages", {}).get(key, "")
    if not template:
        return ""
    try:
        msg = template.format(**kwargs)
    except KeyError:
        msg = template
    return f"{prefix}, {msg}".strip()


@app.post("/api/tts/test")
async def test_tts():
    """Send test TTS using real account data: direct HA API when addon, else MQTT fallback"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    
    # Build test message using real account data
    prefix = config.get('prefix', DEFAULT_TTS_PREFIX)
    
    try:
        ledger = await db.get_ledger_data()
        bills = ledger.get("bills", [])
        latest_bill = bills[0] if bills else {}
        
        # Get balance
        balance = ledger.get("account_balance") or ledger.get("total_balance", "")
        if isinstance(balance, (int, float)):
            balance = f"${balance:.2f}"
        
        # Get latest bill amount
        bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
        
        # Get due date and format for TTS
        due_date_raw = latest_bill.get("due_date", "")
        due_date = ""
        if due_date_raw:
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(due_date_raw)
                due_date = dt.strftime("%B %d").replace(" 0", " ")
            except:
                due_date = due_date_raw
        
        # Get kWh used from bill details
        last_bill_kwh = ""
        latest_bill_id = latest_bill.get("id")
        if latest_bill_id:
            bill_details = await db.get_bill_details(latest_bill_id)
            if bill_details:
                kwh_val = bill_details.get("kwh_used")
                if kwh_val:
                    last_bill_kwh = f"{int(round(kwh_val))} kWh"
        
        # Build message with real data
        if balance and bill_amount:
            full_msg = f"{prefix} Your account balance is {balance}."
            if bill_amount and bill_amount != "N/A":
                full_msg += f" Your latest bill is {bill_amount}"
                if last_bill_kwh:
                    full_msg += f", using {last_bill_kwh}"
                if due_date:
                    full_msg += f", due {due_date}"
                full_msg += "."
        else:
            full_msg = f"{prefix} Con Edison test notification. Your account data will appear here."
    except Exception as e:
        await db.add_log("warning", f"Test TTS failed to get real data: {e}")
        full_msg = f"{prefix} Con Edison test notification."
    
    volume = config.get("volume", 0.7)
    wait_for_idle = config.get("wait_for_idle", True)
    tts_service = config.get("tts_service", "tts.google_translate_say")

    if os.environ.get("SUPERVISOR_TOKEN"):
        from ha_tts import send_tts
        success, err = await send_tts(
            message=full_msg,
            media_player=media_player,
            volume=volume,
            wait_for_idle=wait_for_idle,
            tts_service=tts_service,
        )
        if success:
            return {"success": True, "message": "TTS sent via Home Assistant."}
        raise HTTPException(status_code=500, detail=err or "TTS failed")

    from mqtt_client import get_mqtt_client
    mqtt_client = get_mqtt_client()
    if mqtt_client and mqtt_client.enabled:
        await mqtt_client.publish_tts_request(
            message=full_msg, media_player=media_player, volume=volume, wait_for_idle=wait_for_idle
        )
        return {"success": True, "message": "TTS request sent via MQTT. Add HA automation if not using addon."}
    raise HTTPException(status_code=400, detail="Not in HA addon and MQTT not configured")


@app.post("/api/tts/test-new-bill")
async def test_new_bill_tts():
    """Test new bill TTS using the latest bill data"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    
    # Get latest bill data
    ledger = await db.get_ledger_data()
    bills = ledger.get("bills", [])
    if not bills:
        raise HTTPException(status_code=400, detail="No bills found to test with")
    
    latest_bill = bills[0]
    bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
    month_range = latest_bill.get("month_range", "this month")
    
    # Format due date for TTS
    due_date_raw = latest_bill.get("due_date", "")
    due_date = "soon"
    if due_date_raw:
        try:
            from dateutil import parser as date_parser
            dt = date_parser.parse(due_date_raw)
            due_date = dt.strftime("%B %d").replace(" 0", " ")
        except:
            due_date = due_date_raw
    
    # Trigger the TTS
    from tts_scheduler import trigger_new_bill_tts
    await trigger_new_bill_tts(
        bill_month_range=month_range,
        bill_total=bill_amount,
        due_date=due_date
    )
    
    # Also send push notification
    try:
        from notifications import notify_new_bill
        sent = await notify_new_bill(
            amount=bill_amount,
            due_date=due_date,
            month_range=month_range
        )
        await db.add_log("info", f"Test new bill TTS+notification sent (notifications: {sent})")
    except Exception as e:
        await db.add_log("warning", f"Test new bill notification failed: {e}")
    
    return {
        "success": True, 
        "message": "New bill TTS sent",
        "data": {
            "amount": bill_amount,
            "month_range": month_range,
            "due_date": due_date
        }
    }


@app.post("/api/tts/test-payment")
async def test_payment_tts():
    """Test payment received TTS using the latest payment data"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    
    # Get latest payment data
    ledger = await db.get_ledger_data()
    latest_payment = ledger.get("latest_payment")
    
    if not latest_payment:
        raise HTTPException(status_code=400, detail="No payments found to test with")
    
    payment_amount = latest_payment.get("amount", "N/A")
    payee_name = latest_payment.get("payee_name", "")
    
    # Get current balance
    balance = ledger.get("account_balance") or ledger.get("total_balance", "")
    if isinstance(balance, (int, float)):
        balance = f"${balance:.2f}"
    
    # Trigger the TTS
    from tts_scheduler import trigger_payment_received_tts
    await trigger_payment_received_tts(
        amount=payment_amount,
        balance=balance,
        payee_name=payee_name
    )
    
    # Also send push notification
    try:
        from notifications import notify_payment_received
        sent = await notify_payment_received(
            amount=payment_amount,
            balance=balance,
            payee_name=payee_name
        )
        await db.add_log("info", f"Test payment TTS+notification sent (notifications: {sent})")
    except Exception as e:
        await db.add_log("warning", f"Test payment notification failed: {e}")
    
    return {
        "success": True, 
        "message": "Payment received TTS sent",
        "data": {
            "amount": payment_amount,
            "balance": balance,
            "payee_name": payee_name
        }
    }


@app.post("/api/tts/test-late-fee")
async def test_late_fee_tts():
    """Test late fee TTS using sample data"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")

    from tts_scheduler import trigger_late_fee_tts
    await trigger_late_fee_tts("$3.25")

    try:
        from notifications import notify_late_fee
        sent = await notify_late_fee("$3.25")
        await db.add_log("info", f"Test late fee TTS+notification sent (notifications: {sent})")
    except Exception as e:
        await db.add_log("warning", f"Test late fee notification failed: {e}")

    return {
        "success": True,
        "message": "Late fee TTS sent",
        "data": {"late_fee_amount": "$3.25"}
    }


@app.post("/api/tts/test-payment-claimed")
async def test_payment_claimed_tts():
    """Test payment claimed TTS using sample data"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    from tts_scheduler import trigger_payment_claimed_tts
    await trigger_payment_claimed_tts(payee_name="Sample Payee", amount="$50.00", payment_date="03/15/2026")
    return {"success": True, "message": "Payment claimed TTS sent"}


@app.post("/api/tts/test-payment-unclaimed")
async def test_payment_unclaimed_tts():
    """Test payment unclaimed TTS using sample data"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    from tts_scheduler import trigger_payment_unclaimed_tts
    await trigger_payment_unclaimed_tts(payee_name="Sample Payee", amount="$50.00", payment_date="03/15/2026")
    return {"success": True, "message": "Payment unclaimed TTS sent"}


@app.post("/api/notifications/test-new-bill")
async def test_new_bill_notification():
    """Test new bill push notification only (no TTS)"""
    ledger = await db.get_ledger_data()
    bills = ledger.get("bills", [])
    if not bills:
        raise HTTPException(status_code=400, detail="No bills found to test with")
    
    latest_bill = bills[0]
    bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
    month_range = latest_bill.get("month_range", "this month")
    
    due_date_raw = latest_bill.get("due_date", "")
    due_date = "soon"
    if due_date_raw:
        try:
            from dateutil import parser as date_parser
            dt = date_parser.parse(due_date_raw)
            due_date = dt.strftime("%B %d").replace(" 0", " ")
        except:
            due_date = due_date_raw
    
    from notifications import notify_new_bill
    sent = await notify_new_bill(
        amount=bill_amount,
        due_date=due_date,
        month_range=month_range
    )
    
    return {
        "success": True,
        "sent_count": sent,
        "message": f"New bill notification sent to {sent} device(s)",
        "data": {
            "amount": bill_amount,
            "month_range": month_range,
            "due_date": due_date
        }
    }


@app.post("/api/notifications/test-payment")
async def test_payment_notification():
    """Test payment received push notification only (no TTS)"""
    ledger = await db.get_ledger_data()
    latest_payment = ledger.get("latest_payment")
    
    if not latest_payment:
        raise HTTPException(status_code=400, detail="No payments found to test with")
    
    payment_amount = latest_payment.get("amount", "N/A")
    payee_name = latest_payment.get("payee_name", "")
    
    balance = ledger.get("account_balance") or ledger.get("total_balance", "")
    if isinstance(balance, (int, float)):
        balance = f"${balance:.2f}"
    
    from notifications import notify_payment_received
    sent = await notify_payment_received(
        amount=payment_amount,
        balance=balance,
        payee_name=payee_name
    )
    
    return {
        "success": True,
        "sent_count": sent,
        "message": f"Payment notification sent to {sent} device(s)",
        "data": {
            "amount": payment_amount,
            "balance": balance,
            "payee_name": payee_name
        }
    }


@app.post("/api/notifications/test-due-reminder")
async def test_due_reminder_notification():
    """Test due date reminder push notification"""
    ledger = await db.get_ledger_data()
    bills = ledger.get("bills", [])
    if not bills:
        raise HTTPException(status_code=400, detail="No bills found to test with")
    
    latest_bill = bills[0]
    bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
    
    due_date_raw = latest_bill.get("due_date", "")
    due_date = "soon"
    days_until = 3
    if due_date_raw:
        try:
            from dateutil import parser as date_parser
            from datetime import datetime
            dt = date_parser.parse(due_date_raw)
            due_date = dt.strftime("%B %d").replace(" 0", " ")
            days_until = max(0, (dt - datetime.now()).days)
        except:
            due_date = due_date_raw
    
    from notifications import notify_due_reminder
    sent = await notify_due_reminder(
        amount=bill_amount,
        due_date=due_date,
        days_until=days_until
    )
    
    return {
        "success": True,
        "sent_count": sent,
        "message": f"Due reminder notification sent to {sent} device(s)",
        "data": {
            "amount": bill_amount,
            "due_date": due_date,
            "days_until": days_until
        }
    }


# ========== TTS Schedule Endpoints ==========

class TTSScheduleTimeModel(BaseModel):
    time: str  # "HH:MM" format
    days: Optional[list] = None  # List of day abbreviations: ["mon", "tue", ...]

class TTSScheduleModel(BaseModel):
    enabled: Optional[bool] = None
    hour_pattern: Optional[int] = None  # Announce every N hours
    minute_offset: Optional[int] = None  # Minute within hour
    start_time: Optional[str] = None  # Active hours start "HH:MM"
    end_time: Optional[str] = None  # Active hours end "HH:MM"
    days_of_week: Optional[list] = None  # ["mon", "tue", ...]
    message_template: Optional[str] = None  # Custom message template with placeholders
    current_usage_sensor: Optional[str] = None  # HA sensor entity for current kWh usage
    future_usage_sensor: Optional[str] = None  # HA sensor entity for projected kWh usage
    schedule_times: Optional[list] = None  # Legacy: List of TTSScheduleTimeModel dicts
    schedule_type: Optional[str] = None  # Legacy: "daily" or "specific_days"

@app.get("/api/tts-schedule")
async def get_tts_schedule():
    """Get TTS schedule configuration"""
    from tts_scheduler import get_scheduler
    scheduler = get_scheduler()
    return await scheduler.load_schedule_config()

@app.post("/api/tts-schedule")
async def save_tts_schedule_endpoint(config: TTSScheduleModel):
    """Save TTS schedule configuration"""
    from tts_scheduler import get_scheduler
    scheduler = get_scheduler()
    current = await scheduler.load_schedule_config()
    updates = config.model_dump(exclude_none=True)
    for k, v in updates.items():
        current[k] = v
    await scheduler.save_schedule_config(current)
    
    # Restart scheduler to apply new schedule
    await scheduler.stop()
    await scheduler.start()
    
    return {"success": True}

@app.post("/api/tts/trigger-bill-summary")
async def trigger_bill_summary_tts():
    """Manually trigger a bill summary TTS"""
    from tts_scheduler import get_scheduler
    
    # Use main config loader to ensure consistency
    tts_config = await load_tts_config()

    if not tts_config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled. Enable it in Event TTS Alerts.")
    
    media_player = (tts_config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="No media player configured")
    
    tts_service = (tts_config.get("tts_service") or "").strip()
    if not tts_service:
        raise HTTPException(status_code=400, detail="No TTS entity configured")

    scheduler = get_scheduler()
    await scheduler._send_scheduled_tts(tts_config)
    return {"success": True, "message": "Bill summary TTS triggered"}


@app.get("/api/ha-entities")
async def get_ha_entities():
    """Get Home Assistant entities (media players, TTS services) when running as addon"""
    import aiohttp
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    result = {
        "media_players": [],
        "tts_entities": [],
        "is_addon": bool(token)
    }
    
    if not token:
        return result
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://supervisor/core/api/states",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    await db.add_log("warning", f"Failed to fetch HA states: {resp.status}")
                    return result
                
                states = await resp.json()
                
                for entity in states:
                    entity_id = entity.get("entity_id", "")
                    friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
                    state = entity.get("state", "")
                    
                    if entity_id.startswith("media_player."):
                        result["media_players"].append({
                            "entity_id": entity_id,
                            "friendly_name": friendly_name,
                            "state": state
                        })
                    elif entity_id.startswith("tts."):
                        result["tts_entities"].append({
                            "entity_id": entity_id,
                            "friendly_name": friendly_name
                        })
                
                result["media_players"].sort(key=lambda x: x["friendly_name"])
                result["tts_entities"].sort(key=lambda x: x["friendly_name"])
                
    except Exception as e:
        await db.add_log("error", f"Failed to fetch HA entities: {str(e)}")
    
    return result


@app.get("/api/ha-users")
async def get_ha_users():
    """Get Home Assistant users via websocket API when running as addon"""
    import aiohttp
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    result = {
        "users": [],
        "is_addon": bool(token)
    }
    
    if not token:
        return result
    
    try:
        async with aiohttp.ClientSession() as session:
            # Use websocket API via HTTP POST to get user list
            async with session.post(
                "http://supervisor/core/api/websocket_api",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"type": "config/auth/list"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users = data if isinstance(data, list) else data.get("result", [])
                    for user in users:
                        if user.get("system_generated"):
                            continue
                        result["users"].append({
                            "id": user.get("id"),
                            "name": user.get("name"),
                            "username": user.get("username"),
                            "is_admin": user.get("group_ids", []) and "system-admin" in user.get("group_ids", []),
                            "is_active": user.get("is_active", True)
                        })
                else:
                    # Fallback: try person entities which often mirror users
                    async with session.get(
                        "http://supervisor/core/api/states",
                        headers={"Authorization": f"Bearer {token}"}
                    ) as states_resp:
                        if states_resp.status == 200:
                            states = await states_resp.json()
                            for entity in states:
                                entity_id = entity.get("entity_id", "")
                                if entity_id.startswith("person."):
                                    name = entity.get("attributes", {}).get("friendly_name", entity_id.split(".")[-1])
                                    result["users"].append({
                                        "id": entity_id,
                                        "name": name,
                                        "username": entity_id.split(".")[-1],
                                        "is_admin": False,
                                        "is_active": True
                                    })
                
                result["users"].sort(key=lambda x: x["name"].lower())
                
    except Exception as e:
        await db.add_log("error", f"Failed to fetch HA users: {str(e)}")
    
    return result


@app.get("/api/ha-notify-services")
async def get_ha_notify_services():
    """Get available mobile app notify services from Home Assistant"""
    import aiohttp
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    result = {
        "services": [],
        "is_addon": bool(token)
    }
    
    if not token:
        return result
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://supervisor/core/api/services",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                if resp.status != 200:
                    await db.add_log("warning", f"Failed to fetch HA services: {resp.status}")
                    return result
                
                services = await resp.json()
                
                # Find notify domain and filter for mobile_app services
                for domain in services:
                    if domain.get("domain") == "notify":
                        for service_name in domain.get("services", {}):
                            if service_name.startswith("mobile_app_"):
                                device_name = service_name.replace("mobile_app_", "")
                                friendly_name = device_name.replace("_", " ").title()
                                result["services"].append({
                                    "service": service_name,
                                    "friendly_name": friendly_name,
                                    "full_service": f"notify.{service_name}"
                                })
                
                result["services"].sort(key=lambda x: x["friendly_name"])
                
    except Exception as e:
        await db.add_log("error", f"Failed to fetch HA notify services: {str(e)}")
    
    return result


# =============================================================================
# Notification Config API
# =============================================================================

@app.get("/api/notification-config")
async def get_notification_configs():
    """Get all notification configurations"""
    configs = await db.get_all_notification_configs()
    return {"configs": configs}


class NotificationConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    title: Optional[str] = None
    template: Optional[str] = None
    days_before_due: Optional[int] = None
    reminder_send_time: Optional[str] = None


@app.put("/api/notification-config/{event_type}")
async def update_notification_config_endpoint(event_type: str, data: NotificationConfigUpdate):
    """Update a notification configuration"""
    success = await db.update_notification_config(
        event_type=event_type,
        enabled=data.enabled,
        title=data.title,
        template=data.template,
        days_before_due=data.days_before_due,
        reminder_send_time=data.reminder_send_time
    )
    if not success:
        raise HTTPException(status_code=404, detail="Notification config not found")
    return {"success": True}


async def _get_real_test_data_for_notification(event_type: str) -> dict:
    """Fetch real account data for notification test."""
    ledger = await db.get_ledger_data()
    bills = ledger.get("bills", [])
    latest_bill = bills[0] if bills else {}
    latest_payment = ledger.get("latest_payment")  # Latest payment for current bill
    balance = ledger.get("account_balance") or "$0.00"
    if isinstance(balance, (int, float)):
        balance = f"${balance:.2f}"

    if event_type == "new_bill":
        bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
        due_date_raw = latest_bill.get("due_date", "")
        due_date = "soon"
        if due_date_raw:
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(due_date_raw)
                due_date = dt.strftime("%B %d, %Y").replace(" 0", " ")
            except Exception:
                due_date = due_date_raw
        month_range = latest_bill.get("month_range", "this month")
        return {
            "amount": bill_amount,
            "due_date": due_date,
            "month_range": month_range,
        }

    if event_type == "payment_received":
        if not latest_payment:
            return {"amount": "N/A", "balance": balance, "payee_name": "Unknown"}
        return {
            "amount": latest_payment.get("amount", "N/A"),
            "balance": balance,
            "payee_name": latest_payment.get("payee_name", "") or "Unknown",
        }

    if event_type == "due_reminder":
        bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "N/A")
        due_date_raw = latest_bill.get("due_date", "")
        due_date = "soon"
        days_until = 3
        if due_date_raw:
            try:
                from dateutil import parser as date_parser
                from datetime import datetime
                dt = date_parser.parse(due_date_raw)
                due_date = dt.strftime("%B %d, %Y").replace(" 0", " ")
                days_until = max(0, (dt - datetime.now()).days)
            except Exception:
                due_date = due_date_raw
        days_until_text = "today" if days_until == 0 else f"in {days_until} days"
        return {
            "amount": bill_amount,
            "due_date": due_date,
            "days_until": str(days_until),
            "days_until_text": days_until_text,
        }

    if event_type == "balance_change":
        prev = await db.get_previous_balance()
        old_balance = prev["balance"] if prev else "$0.00"
        curr = await db.get_current_balance()
        new_balance = curr["balance"] if curr else "$0.00"
        return {
            "old_balance": old_balance,
            "new_balance": new_balance,
        }

    if event_type == "late_fee":
        return {"late_fee_amount": "$3.25"}

    if event_type == "payment_claimed":
        payee_name = latest_payment.get("payee_name", "Sample Payee") if latest_payment else "Sample Payee"
        amount = latest_payment.get("amount", "$50.00") if latest_payment else "$50.00"
        payment_date = latest_payment.get("payment_date", "03/15/2026") if latest_payment else "03/15/2026"
        return {"payee_name": payee_name, "amount": amount, "payment_date": payment_date}

    if event_type == "payment_unclaimed":
        payee_name = latest_payment.get("payee_name", "Sample Payee") if latest_payment else "Sample Payee"
        amount = latest_payment.get("amount", "$50.00") if latest_payment else "$50.00"
        payment_date = latest_payment.get("payment_date", "03/15/2026") if latest_payment else "03/15/2026"
        return {"payee_name": payee_name, "amount": amount, "payment_date": payment_date}

    return {}


@app.post("/api/notification-config/test/{event_type}")
async def test_notification(event_type: str, payee_id: Optional[int] = None):
    """Send a test notification for a specific event type using REAL account data."""
    import aiohttp
    from notifications import format_template, ensure_con_edison_title
    
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="Not running as Home Assistant addon")
    
    # Get config
    config = await db.get_notification_config(event_type)
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    
    # Get payees to notify
    if payee_id:
        payees = await db.get_payee_users()
        payee = next((p for p in payees if p["id"] == payee_id), None)
        if not payee or not payee.get("notify_service"):
            raise HTTPException(status_code=400, detail="Payee not found or has no notify service")
        target_payees = [payee]
    else:
        target_payees = await db.get_payees_with_notifications()
        if not target_payees:
            raise HTTPException(status_code=400, detail="No payees with notifications enabled")
    
    # Build test message with REAL account data (same as real triggers)
    test_data = await _get_real_test_data_for_notification(event_type)
    message = format_template(config["template"], test_data)
    
    # Send notifications
    sent_count = 0
    try:
        async with aiohttp.ClientSession() as session:
            for payee in target_payees:
                notify_service = payee.get("notify_service")
                if not notify_service:
                    continue
                
                async with session.post(
                    f"http://supervisor/core/api/services/notify/{notify_service}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "title": ensure_con_edison_title(config.get("title") or ""),
                        "message": message
                    }
                ) as resp:
                    if resp.status == 200:
                        sent_count += 1
                    else:
                        await db.add_log("warning", f"Failed to send test notification to {notify_service}: {resp.status}")
    except Exception as e:
        await db.add_log("error", f"Failed to send test notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"success": True, "sent_count": sent_count, "message": f"Test notification sent to {sent_count} device(s)"}


@app.get("/api/tts/preview-message")
async def preview_tts_message(
    current_sensor: str = None,
    future_sensor: str = None
):
    """Generate preview data for TTS message template variables.
    
    Uses ConEd Connect integration sensors when meter tracking is enabled,
    otherwise falls back to custom sensor configuration.
    """
    from datetime import datetime
    from meter_service import get_meter_service
    from tts_scheduler import get_scheduler

    ledger = await db.get_ledger_data()
    meter_service = get_meter_service()
    meter_enabled = meter_service.is_enabled()

    # Get schedule config for sensors - use query params if provided, otherwise use saved config
    scheduler = get_scheduler()
    schedule_config = await scheduler.load_schedule_config()
    current_usage_sensor = current_sensor if current_sensor else schedule_config.get("current_usage_sensor", "")
    future_usage_sensor = future_sensor if future_sensor else schedule_config.get("future_usage_sensor", "")
    
    # Get time info
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"
    
    hour_12 = hour % 12 or 12
    minute = now.minute
    period = "AM" if hour < 12 else "PM"
    
    if minute == 0:
        time_str = f"{hour_12} {period}"
    elif minute < 10:
        time_str = f"{hour_12} oh {minute} {period}"
    else:
        time_str = f"{hour_12} {minute} {period}"
    
    # Get balance from ledger
    balance = ledger.get("account_balance") or ledger.get("total_balance", "")
    if isinstance(balance, (int, float)):
        balance = f"${balance:.2f}"
    
    # Helper to format date as "Month Day" (no year) for TTS
    def format_date_for_tts(date_str: str) -> str:
        if not date_str:
            return ""
        try:
            from dateutil import parser as date_parser
            dt = date_parser.parse(date_str)
            return dt.strftime("%B %d").replace(" 0", " ")  # "March 15" not "March 05"
        except:
            import re
            match = re.search(r'(\w{3,9})\s+(\d{1,2})', date_str)
            if match:
                return f"{match.group(1)} {int(match.group(2))}"
            return date_str
    
    # Get latest bill from ledger (this matches Account Ledger display)
    bills = ledger.get("bills", [])
    latest_bill = bills[0] if bills else {}
    
    # Get due_date from bill (now included via get_ledger_data)
    due_date_raw = latest_bill.get("due_date", "") or ""
    due_date = format_date_for_tts(due_date_raw)
    
    # Bill amount and period from ledger
    bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "")
    bill_period = latest_bill.get("month_range", "")
    
    # Get kwh_used and kwh_cost from bill_details for the SAME bill from ledger
    last_bill_kwh = ""
    kwh_cost = None
    latest_bill_id = latest_bill.get("id")
    
    if latest_bill_id:
        bill_details = await db.get_bill_details(latest_bill_id)
        if bill_details:
            kwh_val = bill_details.get("kwh_used")
            if kwh_val:
                # Format as whole number for TTS readability
                last_bill_kwh = f"{int(round(kwh_val))} kWh"
            kwh_cost = bill_details.get("kwh_cost")
            if not due_date:
                due_date = format_date_for_tts(bill_details.get("due_date", "") or "")
    
    # Initialize usage variables
    current_usage_kwh = ""
    current_usage_cost = ""
    projected_usage_kwh = ""
    projected_usage_cost = ""
    
    token = os.environ.get("SUPERVISOR_TOKEN")
    
    # If meter tracking is enabled, use the addon's own meter data directly
    if meter_enabled:
        await db.add_log("debug", "TTS Preview: Using addon meter service data (meter tracking enabled)")
        try:
            # Get data directly from meter service - no need to go through HA sensors
            forecast = await meter_service.get_cached_forecast()
            
            # Get kWh cost from bill details
            meter_kwh_cost = kwh_cost
            
            if forecast:
                # Current cycle usage (usage_to_date)
                usage_to_date = forecast.get("usage_to_date")
                if usage_to_date is not None:
                    current_usage_kwh = f"{int(round(usage_to_date))} kWh"
                    if meter_kwh_cost:
                        cost_val = usage_to_date * meter_kwh_cost
                        current_usage_cost = f"${cost_val:.2f}"
                    await db.add_log("debug", f"TTS Preview: usage_to_date={usage_to_date}, cost={current_usage_cost}")
                
                # Forecasted usage
                forecasted = forecast.get("forecasted_usage")
                if forecasted is not None:
                    projected_usage_kwh = f"{int(round(forecasted))} kWh"
                    if meter_kwh_cost:
                        cost_val = forecasted * meter_kwh_cost
                        projected_usage_cost = f"${cost_val:.2f}"
                    await db.add_log("debug", f"TTS Preview: forecasted={forecasted}, cost={projected_usage_cost}")
            else:
                await db.add_log("debug", "TTS Preview: No forecast data available from meter service")
                
        except Exception as e:
            await db.add_log("warning", f"Failed to get meter service data: {e}")
    
    # Fallback to custom sensors if meter tracking not enabled or sensors not populated
    elif token and (current_usage_sensor or future_usage_sensor):
        await db.add_log("debug", f"TTS Preview: Using custom sensors - current='{current_usage_sensor}', future='{future_usage_sensor}'")
        try:
            async with aiohttp.ClientSession() as session:
                # Fetch current usage sensor
                if current_usage_sensor and current_usage_sensor.strip():
                    sensor_id = current_usage_sensor.strip()
                    try:
                        async with session.get(
                            f"http://supervisor/core/api/states/{sensor_id}",
                            headers={"Authorization": f"Bearer {token}"},
                        ) as resp:
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        current_usage_kwh = f"{int(round(kwh_value))} kWh"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            current_usage_cost = f"${cost_value:.2f}"
                                    except ValueError:
                                        current_usage_kwh = f"{sensor_state} kWh"
                    except Exception as e:
                        await db.add_log("warning", f"Failed to fetch current usage sensor: {e}")
                
                # Fetch future usage projection sensor
                if future_usage_sensor and future_usage_sensor.strip():
                    sensor_id = future_usage_sensor.strip()
                    try:
                        async with session.get(
                            f"http://supervisor/core/api/states/{sensor_id}",
                            headers={"Authorization": f"Bearer {token}"},
                        ) as resp:
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        projected_usage_kwh = f"{int(round(kwh_value))} kWh"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            projected_usage_cost = f"${cost_value:.2f}"
                                    except ValueError:
                                        projected_usage_kwh = f"{sensor_state} kWh"
                    except Exception as e:
                        await db.add_log("warning", f"Failed to fetch future usage sensor: {e}")
        except Exception as e:
            await db.add_log("warning", f"Failed to create session for sensor fetch: {e}")
    
    # Get latest payment from ledger
    latest_payment = ledger.get("latest_payment")
    last_payment_amount = ""
    last_payment_date = ""
    
    if latest_payment and isinstance(latest_payment, dict):
        last_payment_amount = latest_payment.get("amount", "")
        last_payment_date = latest_payment.get("payment_date", "")
    
    await db.add_log("debug", f"TTS Preview final: current_usage_kwh='{current_usage_kwh}', current_usage_cost='{current_usage_cost}'")
    
    return {
        "greeting": greeting,
        "time": time_str,
        "balance": balance or "N/A",
        "latest_bill": {
            "amount": bill_amount or "N/A",
            "month_range": bill_period or "N/A",
            "due_date": due_date or "N/A",
            "kwh_used": last_bill_kwh or "N/A"
        },
        "latest_payment": {
            "amount": last_payment_amount or "No payment",
            "payment_date": last_payment_date or ""
        },
        "current_usage": {
            "kwh": current_usage_kwh or "N/A",
            "cost": current_usage_cost or "N/A"
        },
        "projected_usage": {
            "kwh": projected_usage_kwh or "N/A",
            "cost": projected_usage_cost or "N/A"
        },
        "_debug": {
            "sensors_requested": {
                "current": current_usage_sensor,
                "future": future_usage_sensor
            },
            "token_available": bool(token)
        }
    }


# ========== SPA Static Files & Fallback ==========
# Mount /assets for Vue build output (CSS, JS, images)
# Serve index.html for non-API paths (SPA routing)
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir), html=False), name="assets")
    images_dir = FRONTEND_DIST / "images"
    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir), html=False), name="images")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for SPA fallback (non-API, non-asset paths)"""
        # Don't serve SPA for API routes (handled by other routes)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend not built")
else:
    @app.get("/")
    async def root():
        return {"message": "Con Edison API", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
