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
CODE_VERSION = "1.2.0-postgres"

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
MQTT_CONFIG_FILE = DATA_DIR / "mqtt_config.json"
SETTINGS_FILE = DATA_DIR / "app_settings.json"
IMAP_CONFIG_FILE = DATA_DIR / "imap_config.json"
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

class ScheduleModel(BaseModel):
    enabled: bool
    frequency: int  # Frequency in seconds

def load_schedule() -> dict:
    """Load automated scraping schedule"""
    if not SCHEDULE_FILE.exists():
        return {"enabled": False, "frequency": 3600, "last_scrape_end": None, "next_run": None}
    
    try:
        data = json.loads(SCHEDULE_FILE.read_text())
        return {
            "enabled": data.get("enabled", False),
            "frequency": data.get("frequency", 3600),
            "last_scrape_end": data.get("last_scrape_end"),
            "next_run": data.get("next_run")
        }
    except Exception as e:
        logging.error(f"Failed to load schedule: {str(e)}")
        return {"enabled": False, "frequency": 3600, "last_scrape_end": None, "next_run": None}

def save_schedule(enabled: bool, frequency: int, last_scrape_end: str = None, next_run: str = None):
    """Save automated scraping schedule"""
    # Load existing to preserve last_scrape_end if not provided
    existing = load_schedule()
    
    schedule = {
        "enabled": enabled,
        "frequency": frequency,
        "last_scrape_end": last_scrape_end or existing.get("last_scrape_end"),
        "next_run": next_run or existing.get("next_run"),
        "updated_at": utc_now_iso()
    }
    SCHEDULE_FILE.write_text(json.dumps(schedule))
    logging.info(f"Schedule saved: enabled={enabled}, frequency={frequency}s")

def update_last_scrape_time():
    """Update last_scrape_end and calculate next_run after a successful scrape"""
    schedule = load_schedule()
    now = datetime.now(timezone.utc)
    next_run = now + timedelta(seconds=schedule["frequency"])
    
    schedule["last_scrape_end"] = now.isoformat()
    schedule["next_run"] = next_run.isoformat()
    schedule["updated_at"] = utc_now_iso()
    SCHEDULE_FILE.write_text(json.dumps(schedule))

async def run_scheduled_scrape():
    """Run a scheduled scrape"""
    global _scrape_running
    import time as time_module
    start_time = time_module.time()
    
    _scrape_running = True
    try:
        credentials = load_credentials()
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
        
        # Send notifications via MQTT
        from mqtt_client import get_mqtt_client
        mqtt_client = get_mqtt_client()
        
        if success and scraped_data:
            timestamp = scraped_data.get("timestamp")
            
            # MQTT: Always publish after every successful scrape
            if mqtt_client:
                if scraped_data.get("account_balance"):
                    await mqtt_client.publish_account_balance(scraped_data["account_balance"], timestamp)
                
                if scraped_data.get("bill_history"):
                    bill_history = scraped_data["bill_history"]
                    ledger = bill_history.get("ledger", [])
                    bills = [item for item in ledger if item.get("type") == "bill"]
                    
                    if len(bills) > 0:
                        await mqtt_client.publish_latest_bill(bills[0], timestamp)
                    if len(bills) >= 2:
                        await mqtt_client.publish_previous_bill(bills[1], timestamp)
                    
                    # Smart last payment detection for MQTT only
                    should_pub, last_payment, reason = await should_publish_last_payment()
                    if should_pub and last_payment:
                        await db.add_log("info", f"Publishing last_payment to MQTT: {reason}")
                        await mqtt_client.publish_last_payment(last_payment, timestamp)
                    else:
                        await db.add_log("debug", f"Skipping last_payment MQTT: {reason if reason else 'no change'}")
                
                # Publish payee summary for the most recent bill (scheduled scrape)
                try:
                    # Using db module for database operations
                    all_summaries = await db.calculate_all_payee_balances()
                    all_bills = await db.get_all_bills()
                    if all_bills and len(all_bills) > 0:
                        most_recent_bill = all_bills[0]
                        bill_id = most_recent_bill.get('id')
                        if bill_id and bill_id in all_summaries:
                            summary = all_summaries[bill_id]
                            bill_info = {
                                'bill_cycle_date': most_recent_bill.get('bill_cycle_date', ''),
                                'bill_total': summary.get('bill_total', 0),
                                'total_paid': summary.get('total_paid', 0),
                                'bill_balance': summary.get('bill_balance', 0),
                                'bill_status': summary.get('bill_status', 'unknown')
                            }
                            payee_summaries = summary.get('payee_summaries', [])
                            await mqtt_client.publish_payee_summary(payee_summaries, bill_info, timestamp)
                            await db.add_log("info", "Published payee summary to MQTT")
                except Exception as e:
                    await db.add_log("warning", f"Failed to publish payee summary: {e}")
            
            # ==========================================
            # INDEPENDENT TTS TRIGGERS (not tied to MQTT)
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
                        month_range=tts_bill_data.get("month_range", ""),
                        amount=tts_bill_data.get("bill_total", ""),
                        due_date=tts_bill_data.get("due_date", "")
                    )
                else:
                    await db.add_log("debug", f"No bill TTS: {tts_bill_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger bill TTS: {tts_e}")
        
        # Check IMAP for payment attribution if configured
        if success:
            try:
                from imap_client import load_imap_config, run_imap_auto_attribution
                imap_config = load_imap_config()
                if imap_config.get('auto_assign_mode') == 'every_scrape' and imap_config.get('server'):
                    await db.add_log("info", "Running IMAP payment attribution after scrape...")
                    await run_imap_auto_attribution()
            except Exception as imap_e:
                await db.add_log("warning", f"IMAP auto-attribution failed: {imap_e}")
            
            # Auto-assign expired pending payments to default payee
            try:
                # Auto-assign expired pending payments
                await db.auto_assign_expired_pending_payments()
                result = {"message": "Auto-assigned expired pending payments"}
                if result.get('assigned', 0) > 0:
                    await db.add_log("info", result.get('message', 'Auto-assigned expired pending payments'))
            except Exception as auto_e:
                await db.add_log("warning", f"Auto-assign expired payments failed: {auto_e}")
        
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
            schedule = load_schedule()
            
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
                current_schedule = load_schedule()
                if current_schedule["enabled"]:
                    await run_scheduled_scrape()
                    # Update next run time after scrape completes
                    update_last_scrape_time()
            else:
                # If disabled, check every 60 seconds
                await asyncio.sleep(60)
        except Exception as e:
            error_msg = f"Scheduler error: {str(e)}"
            await db.add_log("error", error_msg)
            logging.error(error_msg)
            await asyncio.sleep(60)  # Wait before retrying

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
    schedule = load_schedule()
    if schedule["enabled"]:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        await db.add_log("info", "Scheduler restarted")
    else:
        await db.add_log("info", "Scheduler disabled")

# Start scheduler on app startup
@app.on_event("startup")
async def startup_event():
    global _scheduler_task
    
    # Initialize MQTT client from saved configuration
    try:
        from mqtt_client import init_mqtt_client
        mqtt_config = load_mqtt_config()
        if mqtt_config.get("mqtt_url"):
            init_mqtt_client(
                mqtt_config.get("mqtt_url", ""),
                mqtt_config.get("mqtt_username", ""),
                mqtt_config.get("mqtt_password", ""),
                mqtt_config.get("mqtt_base_topic", "coned"),
                mqtt_config.get("mqtt_qos", 1),
                mqtt_config.get("mqtt_retain", True),
                mqtt_config.get("mqtt_discovery", True),
            )
            await db.add_log("info", "MQTT client initialized")
    except Exception as e:
        await db.add_log("warning", f"MQTT initialization failed: {e}")
    
    schedule = load_schedule()
    if schedule["enabled"]:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        await db.add_log("info", f"Scheduler started with {schedule['frequency']}s frequency")
    
    # Start TTS scheduler
    try:
        from tts_scheduler import get_scheduler
        tts_scheduler = get_scheduler()
        await tts_scheduler.start()
        await db.add_log("info", "TTS scheduler started")
    except Exception as e:
        await db.add_log("warning", f"TTS scheduler initialization failed: {e}")
    
    # Publish bill details sensors on startup (due date, kWh cost)
    try:
        await _publish_bill_details_sensors()
    except Exception as e:
        await db.add_log("warning", f"Failed to publish bill details sensors on startup: {e}")
    
    # Initialize meter tracking service
    try:
        from meter_service import init_meter_service
        await init_meter_service()
        await db.add_log("info", "Meter tracking service initialized")
    except Exception as e:
        await db.add_log("warning", f"Meter tracking service initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
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

class MQTTConfigModel(BaseModel):
    mqtt_url: str = ""
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_base_topic: str = "coned"
    mqtt_qos: int = 1
    mqtt_retain: bool = True
    mqtt_discovery: bool = True

class AppSettingsModel(BaseModel):
    time_offset_hours: float = 0.0
    settings_password: str = "0000"

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(encrypted_data.encode()).decode()

def save_credentials(username: str, password: str, totp_secret: str):
    """Save encrypted credentials"""
    credentials = {
        "username": encrypt_data(username),
        "password": encrypt_data(password),
        "totp_secret": encrypt_data(totp_secret)
    }
    CREDENTIALS_FILE.write_text(json.dumps(credentials))

def load_credentials() -> Optional[dict]:
    """Load and decrypt credentials"""
    if not CREDENTIALS_FILE.exists():
        return None
    
    try:
        data = json.loads(CREDENTIALS_FILE.read_text())
        return {
            "username": decrypt_data(data["username"]),
            "password": decrypt_data(data["password"]),
            "totp_secret": decrypt_data(data["totp_secret"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load credentials: {str(e)}")

def save_mqtt_config(mqtt_config: dict):
    """Save MQTT configuration to file"""
    config_data = {
        "mqtt_url": mqtt_config.get("mqtt_url", ""),
        "mqtt_username": mqtt_config.get("mqtt_username", ""),
        "mqtt_password": encrypt_data(mqtt_config.get("mqtt_password", "")),  # Encrypt password
        "mqtt_base_topic": mqtt_config.get("mqtt_base_topic", "coned"),
        "mqtt_qos": mqtt_config.get("mqtt_qos", 1),
        "mqtt_retain": mqtt_config.get("mqtt_retain", True),
        "mqtt_discovery": mqtt_config.get("mqtt_discovery", True),
        "updated_at": utc_now_iso()
    }
    MQTT_CONFIG_FILE.write_text(json.dumps(config_data))

def load_mqtt_config() -> dict:
    """Load MQTT configuration from file"""
    if not MQTT_CONFIG_FILE.exists():
        return {}
    
    try:
        data = json.loads(MQTT_CONFIG_FILE.read_text())
        return {
            "mqtt_url": data.get("mqtt_url", ""),
            "mqtt_username": data.get("mqtt_username", ""),
            "mqtt_password": decrypt_data(data.get("mqtt_password", "")) if data.get("mqtt_password") else "",
            "mqtt_base_topic": data.get("mqtt_base_topic", "coned"),
            "mqtt_qos": data.get("mqtt_qos", 1),
            "mqtt_retain": data.get("mqtt_retain", True),
            "mqtt_discovery": data.get("mqtt_discovery", True),
        }
    except Exception as e:
        logging.warning(f"Failed to load MQTT config: {str(e)}")
        return {}

def load_last_payment_state() -> dict:
    """Load the last known payment state for MQTT change detection"""
    if not LAST_PAYMENT_STATE_FILE.exists():
        return {"bill_id": None, "payment_count": 0, "last_payment_id": None, "last_payment_amount": None}
    
    try:
        return json.loads(LAST_PAYMENT_STATE_FILE.read_text())
    except Exception as e:
        logging.warning(f"Failed to load last payment state: {str(e)}")
        return {"bill_id": None, "payment_count": 0, "last_payment_id": None, "last_payment_amount": None}

def save_last_payment_state(state: dict):
    """Save the last known payment state for MQTT change detection"""
    try:
        LAST_PAYMENT_STATE_FILE.write_text(json.dumps(state))
    except Exception as e:
        logging.warning(f"Failed to save last payment state: {str(e)}")

async def should_publish_last_payment() -> tuple:
    """
    Check if we should publish last_payment to MQTT.
    Returns (should_publish: bool, last_payment_data: dict or None, reason: str)
    
    Last payment is ALWAYS from the most recent billing cycle only.
    
    Only publish when:
    1. Payment count for most recent bill increased (new payment added)
    2. Manual audit changed WHICH payment is the "last" one (different payment ID)
    3. New billing cycle started
    4. First time publishing (no previous state) - including "no payment" state
    
    Does NOT publish when:
    - Just payee attribution changed (payee doesn't affect last_payment MQTT)
    - Order changed but same payment is still "last"
    """
    current_state = await db.get_most_recent_bill_payment_count()
    previous_state = load_last_payment_state()
    
    current_bill_id = current_state.get("bill_id")
    current_count = current_state.get("payment_count", 0)
    
    # Use last payment from the MOST RECENT billing cycle only (not across all bills)
    latest_payment = current_state.get("last_payment")
    bill_cycle_date = current_state.get("bill_cycle_date", "")
    
    previous_bill_id = previous_state.get("bill_id")
    previous_count = previous_state.get("payment_count", 0)
    previous_last_payment_id = previous_state.get("last_payment_id")
    previous_last_amount = previous_state.get("last_payment_amount")
    
    should_publish = False
    reason = ""
    
    # Handle no payments case
    if not latest_payment:
        # Check if we've published "no payment" state before
        if previous_last_payment_id is None and previous_state.get("bill_id") is not None:
            return False, None, "No payments found (already published)"
        # First time or state reset - publish "no payment" state
        if current_bill_id is not None:
            new_state = {
                "bill_id": current_bill_id,
                "payment_count": 0,
                "last_payment_id": None,
                "last_payment_amount": None
            }
            save_last_payment_state(new_state)
            return True, None, "No payments - publishing empty state"
        return False, None, "No bills or payments found"
    
    current_last_id = latest_payment.get("id")
    current_last_amount = latest_payment.get("amount")
    
    # Case 1: New billing cycle
    if current_bill_id != previous_bill_id:
        should_publish = True
        reason = "New billing cycle detected"
    
    # Case 2: Payment count increased (new payment added)
    elif current_count > previous_count:
        should_publish = True
        reason = f"Payment count increased from {previous_count} to {current_count}"
    
    # Case 3: Different payment is now the "last" one (manual audit reordered)
    elif current_last_id != previous_last_payment_id:
        should_publish = True
        reason = "Last payment changed (different payment is now first)"
    
    # Case 4: Same payment but amount changed (shouldn't happen normally)
    elif current_last_amount != previous_last_amount:
        should_publish = True
        reason = "Last payment amount changed"
    
    # NOTE: Payee changes do NOT trigger MQTT - last_payment only cares about amount/date
    
    # Update stored state
    new_state = {
        "bill_id": current_bill_id,
        "payment_count": current_count,
        "last_payment_id": current_last_id,
        "last_payment_amount": current_last_amount
    }
    save_last_payment_state(new_state)
    
    # Augment payment with bill_cycle_date for MQTT payload
    payment_to_publish = dict(latest_payment) if latest_payment else None
    if payment_to_publish and bill_cycle_date:
        payment_to_publish["bill_cycle_date"] = bill_cycle_date
    
    return should_publish, payment_to_publish, reason


# ==========================================
# INDEPENDENT TTS TRIGGER DETECTION
# These functions detect changes independently of MQTT
# ==========================================

def load_tts_payment_state() -> dict:
    """Load the last known payment state for TTS trigger detection"""
    if not TTS_PAYMENT_STATE_FILE.exists():
        return {"bill_id": None, "payment_count": 0, "last_payment_id": None}
    try:
        return json.loads(TTS_PAYMENT_STATE_FILE.read_text())
    except Exception as e:
        logging.warning(f"Failed to load TTS payment state: {str(e)}")
        return {"bill_id": None, "payment_count": 0, "last_payment_id": None}

def save_tts_payment_state(state: dict):
    """Save the TTS payment state"""
    try:
        TTS_PAYMENT_STATE_FILE.write_text(json.dumps(state))
    except Exception as e:
        logging.warning(f"Failed to save TTS payment state: {str(e)}")

def load_tts_bill_state() -> dict:
    """Load the last known bill state for TTS trigger detection"""
    if not TTS_BILL_STATE_FILE.exists():
        return {"latest_bill_id": None, "bill_total": None}
    try:
        return json.loads(TTS_BILL_STATE_FILE.read_text())
    except Exception as e:
        logging.warning(f"Failed to load TTS bill state: {str(e)}")
        return {"latest_bill_id": None, "bill_total": None}

def save_tts_bill_state(state: dict):
    """Save the TTS bill state"""
    try:
        TTS_BILL_STATE_FILE.write_text(json.dumps(state))
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
    previous_state = load_tts_payment_state()
    
    current_bill_id = current_state.get("bill_id")
    current_count = current_state.get("payment_count", 0)
    
    # Get the latest payment from the MOST RECENT billing cycle only
    latest_payment = current_state.get("last_payment")
    
    previous_bill_id = previous_state.get("bill_id")
    previous_count = previous_state.get("payment_count", 0)
    previous_last_payment_id = previous_state.get("last_payment_id")
    
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
        save_tts_payment_state(new_state)
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
    
    # Case 3: First time with state - don't trigger to avoid false positives on first run
    # (User may have existing payments we shouldn't announce)
    
    # Update state
    new_state = {
        "bill_id": current_bill_id,
        "payment_count": current_count,
        "last_payment_id": current_last_id
    }
    save_tts_payment_state(new_state)
    
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
    previous_state = load_tts_bill_state()
    
    if not all_bills or len(all_bills) == 0:
        return False, None, "No bills found"
    
    latest_bill = all_bills[0]
    current_bill_id = latest_bill.get("id")
    previous_bill_id = previous_state.get("latest_bill_id")
    
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
    
    # Case 2: First time - just initialize state, don't trigger
    # (Avoid announcing existing bills on first run)
    
    # Update state
    new_state = {
        "latest_bill_id": current_bill_id,
        "bill_total": latest_bill.get("bill_total")
    }
    save_tts_bill_state(new_state)
    
    return should_trigger, bill_data, reason


def save_app_settings(settings: dict):
    """Save app settings (time offset, password) to file"""
    settings_data = {
        "time_offset_hours": float(settings.get("time_offset_hours", 0.0)),
        "settings_password": encrypt_data(settings.get("settings_password", "0000")),
        "updated_at": utc_now_iso()
    }
    SETTINGS_FILE.write_text(json.dumps(settings_data))

def load_app_settings() -> dict:
    """Load app settings from file"""
    if not SETTINGS_FILE.exists():
        # Create default settings
        default_settings = {
            "time_offset_hours": 0.0,
            "settings_password": "0000",
        }
        save_app_settings(default_settings)
        return default_settings
    
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        return {
            "time_offset_hours": float(data.get("time_offset_hours", 0.0)),
            "settings_password": decrypt_data(data.get("settings_password", encrypt_data("0000"))) if data.get("settings_password") else "0000",
        }
    except Exception as e:
        logging.warning(f"Failed to load app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "settings_password": "0000"}

def verify_settings_password(password: str) -> bool:
    """Verify settings password"""
    settings = load_app_settings()
    return settings.get("settings_password") == password

# Frontend SPA - path to Vue build output (set by Dockerfile or dev)
_SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = _SCRIPT_DIR.parent / "frontend" / "dist"
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = _SCRIPT_DIR / "frontend" / "dist"

@app.get("/api/totp")
async def get_totp():
    """Get current TOTP code"""
    try:
        credentials = load_credentials()
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
            existing_creds = load_credentials()
            if existing_creds:
                password = existing_creds["password"]
                await db.add_log("info", "Using existing password")
            else:
                raise HTTPException(status_code=400, detail="Password is required for new credentials")
        else:
            password = credentials.password
        
        # Save credentials
        save_credentials(
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
        credentials = load_credentials()
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
    
    credentials = load_credentials()
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
            error_msg = result.get('error', 'Login failed')
            await db.add_log("error", f"Login test failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Login test error: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/scrape")
async def start_scraper():
    """Start scraper automation"""
    import time as time_module
    start_time = time_module.time()
    
    from browser_automation import perform_login
    
    credentials = load_credentials()
    if not credentials:
        add_scrape_history(False, "No credentials found", "credentials_check", 0)
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
        
        # Send notifications via MQTT
        from mqtt_client import get_mqtt_client
        mqtt_client = get_mqtt_client()
        
        if success and scraped_data:
            timestamp = scraped_data.get("timestamp")
            
            # MQTT: Publish after every successful scrape
            if mqtt_client:
                if scraped_data.get("account_balance"):
                    await mqtt_client.publish_account_balance(scraped_data["account_balance"], timestamp)
                
                if scraped_data.get("bill_history"):
                    bill_history = scraped_data["bill_history"]
                    ledger = bill_history.get("ledger", [])
                    bills = [item for item in ledger if item.get("type") == "bill"]
                    
                    if len(bills) > 0:
                        await mqtt_client.publish_latest_bill(bills[0], timestamp)
                    if len(bills) >= 2:
                        await mqtt_client.publish_previous_bill(bills[1], timestamp)
                    
                    # Smart last payment detection for MQTT only
                    should_pub, last_payment, reason = await should_publish_last_payment()
                    if should_pub and last_payment:
                        await db.add_log("info", f"Publishing last_payment to MQTT: {reason}")
                        await mqtt_client.publish_last_payment(last_payment, timestamp)
                    else:
                        await db.add_log("debug", f"Skipping last_payment MQTT: {reason if reason else 'no change'}")
                
                # Publish payee summary for the most recent bill (manual scrape)
                try:
                    # Using db module for database operations
                    all_summaries = await db.calculate_all_payee_balances()
                    all_bills = await db.get_all_bills()
                    if all_bills and len(all_bills) > 0:
                        most_recent_bill = all_bills[0]
                        bill_id = most_recent_bill.get('id')
                        if bill_id and bill_id in all_summaries:
                            summary = all_summaries[bill_id]
                            bill_info = {
                                'bill_cycle_date': most_recent_bill.get('bill_cycle_date', ''),
                                'bill_total': summary.get('bill_total', 0),
                                'total_paid': summary.get('total_paid', 0),
                                'bill_balance': summary.get('bill_balance', 0),
                                'bill_status': summary.get('bill_status', 'unknown')
                            }
                            payee_summaries = summary.get('payee_summaries', [])
                            await mqtt_client.publish_payee_summary(payee_summaries, bill_info, timestamp)
                            await db.add_log("info", "Published payee summary to MQTT")
                except Exception as e:
                    await db.add_log("warning", f"Failed to publish payee summary: {e}")
            
            # ==========================================
            # INDEPENDENT TTS TRIGGERS (not tied to MQTT)
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
                        month_range=tts_bill_data.get("month_range", ""),
                        amount=tts_bill_data.get("bill_total", ""),
                        due_date=tts_bill_data.get("due_date", "")
                    )
                else:
                    await db.add_log("debug", f"No bill TTS: {tts_bill_reason}")
            except Exception as tts_e:
                await db.add_log("warning", f"Failed to check/trigger bill TTS: {tts_e}")
        
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

@app.post("/api/mqtt-config")
async def configure_mqtt(config: MQTTConfigModel):
    """Configure MQTT settings"""
    try:
        from mqtt_client import init_mqtt_client
        
        # Build MQTT config dict
        mqtt_config = {
            "mqtt_url": config.mqtt_url.strip(),
            "mqtt_username": config.mqtt_username.strip(),
            "mqtt_password": config.mqtt_password.strip(),
            "mqtt_base_topic": config.mqtt_base_topic.strip() or "coned",
            "mqtt_qos": config.mqtt_qos,
            "mqtt_retain": config.mqtt_retain,
            "mqtt_discovery": config.mqtt_discovery,
        }
        
        # Save to file for persistence
        save_mqtt_config(mqtt_config)
        
        # Initialize MQTT client with new config
        if mqtt_config.get("mqtt_url"):
            init_mqtt_client(
                mqtt_config["mqtt_url"],
                mqtt_config["mqtt_username"],
                mqtt_config["mqtt_password"],
                mqtt_config["mqtt_base_topic"],
                mqtt_config["mqtt_qos"],
                mqtt_config["mqtt_retain"],
                mqtt_config.get("mqtt_discovery", True),
            )
            await db.add_log("success", "MQTT configured successfully")
            # Trigger connect + discovery so sensors appear immediately
            from mqtt_client import get_mqtt_client
            mqtt_client = get_mqtt_client()
            if mqtt_client:
                await mqtt_client.connect()
                await mqtt_client.publish_discovery()
        else:
            await db.add_log("info", "MQTT disabled (no URL provided)")
        
        return {"message": "MQTT configured successfully"}
    except Exception as e:
        error_msg = f"Failed to configure MQTT: {str(e)}"
        await db.add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/mqtt-config")
async def get_mqtt_config():
    """Get current MQTT configuration"""
    try:
        mqtt_config = load_mqtt_config()
        # Don't return the password
        return {
            "mqtt_url": mqtt_config.get("mqtt_url", ""),
            "mqtt_username": mqtt_config.get("mqtt_username", ""),
            "mqtt_password": "***" * (len(mqtt_config.get("mqtt_password", "")) if mqtt_config.get("mqtt_password") else 0),
            "mqtt_base_topic": mqtt_config.get("mqtt_base_topic", "coned"),
            "mqtt_qos": mqtt_config.get("mqtt_qos", 1),
            "mqtt_retain": mqtt_config.get("mqtt_retain", True),
            "mqtt_discovery": mqtt_config.get("mqtt_discovery", True),
        }
    except Exception as e:
        await db.add_log("error", f"Failed to get MQTT config: {str(e)}")
        return {
            "mqtt_url": "",
            "mqtt_username": "",
            "mqtt_password": "",
            "mqtt_base_topic": "coned",
            "mqtt_qos": 1,
            "mqtt_retain": True,
            "mqtt_discovery": True,
        }

@app.post("/api/mqtt-cleanup")
async def cleanup_mqtt_sensors():
    """Remove all MQTT discovery messages (clears retained sensors from broker).
    
    Use this to fix duplicate sensor issues - it publishes empty retained messages
    to all discovery topics, which tells Home Assistant to remove those sensors.
    After running this, restart the addon to re-register sensors cleanly.
    """
    try:
        mqtt_config = load_mqtt_config()
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
        save_app_settings(settings_dict)
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
        settings = load_app_settings()
        # Don't return the actual password, just whether one exists
        return {
            "time_offset_hours": settings.get("time_offset_hours", 0.0),
            "has_password": bool(settings.get("settings_password")),
            "settings_password": settings.get("settings_password", "0000"),  # Needed for preservation
        }
    except Exception as e:
        await db.add_log("error", f"Failed to get app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "has_password": True, "settings_password": "0000"}

class PasswordVerifyModel(BaseModel):
    password: str

@app.post("/api/app-settings/verify-password")
async def verify_password_endpoint(data: PasswordVerifyModel):
    """Verify settings password"""
    try:
        is_valid = verify_settings_password(data.password)
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
        settings = load_app_settings()
        settings['settings_password'] = data.new_password
        save_app_settings(settings)
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
        settings = load_app_settings()
        settings['settings_password'] = data.new_password
        save_app_settings(settings)
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
    data = get_all_scraped_data(limit)
    return {"data": data}

@app.get("/api/scraped-data/latest")
async def get_latest_data():
    """Get latest scraped data"""
    data = get_latest_scraped_data(1)
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
    """Download PDF from URL and store for bill_id. Returns {success, message, size_bytes}."""
    import aiohttp
    import os
    
    if not ('blob.core.windows.net' in pdf_url or '.pdf' in pdf_url.lower() or 'cecony' in pdf_url.lower()):
        await db.add_log("warning", f"URL doesn't look like a ConEd PDF: {pdf_url[:50]}...")
    
    bill = await db.get_bill_by_id(bill_id) if bill_id else None
    if bill_id and not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 200:
                await db.add_log("error", f"PDF download failed: HTTP {response.status}")
                raise HTTPException(status_code=400, detail=f"Failed to download: HTTP {response.status}")
            pdf_content = await response.read()
            if len(pdf_content) < 1000:
                raise HTTPException(status_code=400, detail="Downloaded file too small to be valid PDF")
    
    bills_dir = DATA_DIR / "bills"
    bills_dir.mkdir(exist_ok=True)
    pdf_path = bills_dir / f"bill_{bill_id}.pdf"
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_content)
    await db.upsert_bill_document(bill_id, f"bills/bill_{bill_id}.pdf", source_url=pdf_url)
    size_kb = round(len(pdf_content) / 1024, 1)
    await db.add_log("success", f"PDF saved for bill {bill_id}: {size_kb} KB")
    
    # Parse PDF and extract bill details
    try:
        from pdf_parser import parse_coned_bill_pdf
        # Using db module for database operations
        parsed_data = parse_coned_bill_pdf(str(pdf_path))
        if "error" not in parsed_data:
            await db.upsert_bill_details(bill_id, **parsed_data)
            await db.add_log("info", f"Parsed bill details: kWh={parsed_data.get('kwh_used')}, due={parsed_data.get('due_date')}")
        else:
            await db.add_log("warning", f"PDF parsing error: {parsed_data.get('error')}")
    except Exception as parse_e:
        await db.add_log("warning", f"Failed to parse PDF: {parse_e}")
    
    return {"success": True, "message": f"PDF saved ({size_kb} KB)", "size_bytes": len(pdf_content)}

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
    await _publish_bill_pdf_mqtt()
    await _publish_bill_details_sensors()
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
    await _publish_bill_pdf_mqtt()
    await _publish_bill_details_sensors()
    return result


async def _publish_bill_details_sensors():
    """Publish due_date, kwh_cost, kwh_used sensors via MQTT"""
    from mqtt_client import get_mqtt_client
    client = get_mqtt_client()
    if client and client.enabled:
        try:
            await client.publish_bill_details_sensors()
        except Exception as e:
            await db.add_log("warning", f"Failed to publish bill details sensors: {e}")

async def _get_ha_external_base_url() -> str | None:
    """Get Home Assistant external URL when running as addon. Returns base URL for addon ingress or None."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get external URL from HA config
            async with session.get(
                "http://supervisor/core/api/config",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                external = (data.get("external_url") or "").rstrip("/")
                if not external:
                    return None
            
            # Get the addon's ingress token from supervisor
            async with session.get(
                "http://supervisor/addons/self/info",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    await db.add_log("debug", f"Could not get addon info: HTTP {resp.status}")
                    return None
                addon_data = await resp.json()
                addon_info = addon_data.get("data", {})
                ingress_entry = addon_info.get("ingress_entry", "")
                
                # ingress_entry is like "/api/hassio_ingress/glF8P3O4ySwGrxsHqRBRAOBvR1VRauNQXhAfmqyCCSs"
                if ingress_entry:
                    return f"{external}{ingress_entry}"
                
                # Fallback: try ingress_token directly
                ingress_token = addon_info.get("ingress_token", "")
                if ingress_token:
                    return f"{external}/api/hassio_ingress/{ingress_token}"
                
                await db.add_log("debug", "No ingress_entry or ingress_token found in addon info")
                return None
    except Exception as e:
        await db.add_log("debug", f"Could not get HA external URL: {e}")
        return None


async def _publish_bill_pdf_mqtt():
    """Publish bill PDF URLs to MQTT (state=latest, attributes=all). Uses HA external URL."""
    from mqtt_client import get_mqtt_client
    mqtt_client = get_mqtt_client()
    if not mqtt_client:
        return
    base_url = await _get_ha_external_base_url()
    if not base_url:
        await db.add_log("warning", "Could not get Home Assistant external URL (addon only), skipping MQTT PDF publish")
        return
    await mqtt_client.publish_bill_pdf_url_all(base_url, utc_now_iso())

@app.post("/api/latest-bill-pdf/send-mqtt")
async def send_pdf_url_mqtt():
    """Manually send bill PDF URLs to Home Assistant via MQTT"""
    if await db.get_latest_bill_id_with_document() is None:
        raise HTTPException(status_code=404, detail="No PDF available to send")
    try:
        await _publish_bill_pdf_mqtt()
        return {"success": True, "message": "PDF URLs sent to MQTT"}
    except HTTPException:
        raise
    except Exception as e:
        await db.add_log("error", f"Failed to send PDF URL via MQTT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")

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
                await db.upsert_bill_details(bill_id, **parsed_data)
                results["success"] += 1
                await db.add_log("info", f"Re-parsed bill {bill_id}: kWh={parsed_data.get('kwh_used')}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Bill {bill_id}: {str(e)}")
    
    # Publish updated sensors
    await _publish_bill_details_sensors()
    
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
    schedule = load_schedule()
    
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
        existing = load_schedule()
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
        
        save_schedule(schedule.enabled, schedule.frequency, last_scrape_end, next_run)
        
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
    """Get payments that need payee verification"""
    try:
        payments = await db.get_unverified_payments()
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# PAYEE USER MANAGEMENT
# ==========================================

class PayeeUserModel(BaseModel):
    name: str
    is_default: bool = False

class PayeeUserUpdateModel(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserCardModel(BaseModel):
    user_id: int
    card_last_four: str
    label: Optional[str] = None

class PaymentAttributionModel(BaseModel):
    payment_id: int
    user_id: int
    method: str = "manual"

@app.get("/api/payee-users")
async def list_payee_users():
    """Get all payee users with their cards"""
    try:
        users = await db.get_payee_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payee-users")
async def create_user(user: PayeeUserModel):
    """Create a new payee user"""
    try:
        new_user = await db.create_payee_user(user.name, user.is_default)
        user_id = new_user.id
        await db.add_log("info", f"Created payee user: {user.name}")
        return {"id": user_id, "name": user.name, "is_default": user.is_default}
    except Exception as e:
        if "UNIQUE constraint" in str(e):
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
        await db.update_payee_user(user_id, user.name, user.is_default, user.is_admin)
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

@app.get("/api/payee-users/{user_id}/cards")
async def list_user_cards(user_id: int):
    """Get all cards for a payee user"""
    try:
        cards = await db.get_user_cards(user_id)
        return {"cards": cards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user-cards")
async def add_card(card: UserCardModel):
    """Add a card to a user"""
    try:
        new_card = await db.add_user_card(card.user_id, card.card_last_four, card.label)
        card_id = new_card.id
        await db.add_log("info", f"Added card *{card.card_last_four} to user ID: {card.user_id}")
        return {"id": card_id}
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=400, detail="This card ending is already registered")
        raise HTTPException(status_code=500, detail=str(e))

class UserCardUpdateModel(BaseModel):
    card_label: Optional[str] = None

@app.put("/api/user-cards/{card_id}")
async def update_card(card_id: int, update: UserCardUpdateModel):
    """Update a card's label"""
    try:
        updated = await db.update_user_card(card_id, update.card_label)
        if updated:
            return {"success": True}
        raise HTTPException(status_code=404, detail="Card not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/user-cards/{card_id}")
async def remove_card(card_id: int):
    """Remove a card"""
    try:
        deleted = await db.delete_user_card(card_id)
        if deleted:
            return {"success": True}
        raise HTTPException(status_code=404, detail="Card not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/attribute")
async def attribute_payment_to_user(attribution: PaymentAttributionModel):
    """Attribute a payment to a user"""
    try:
        success = await db.attribute_payment(attribution.payment_id, attribution.user_id, attribution.method)
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
    """Clear payment attribution (unassign from user)"""
    try:
        success = await db.clear_payment_attribution(payment_id)
        if success:
            await db.add_log("info", f"Cleared attribution for payment {payment_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
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
        await db.wipe_bills_and_payments()
        result = {"status": "success", "message": "Database wiped"}
        await db.add_log("warning", f"Database wiped: {result['bills_deleted']} bills, {result['payments_deleted']} payments deleted")
        return {"success": True, **result}
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

# ==========================================
# IMAP EMAIL CONFIGURATION
# ==========================================

class IMAPConfigModel(BaseModel):
    enabled: bool = False
    server: str
    port: int = 993
    email: str
    password: str
    use_ssl: bool = True
    gmail_label: str = "ConEd"
    subject_filter: str = "Payment Confirmation"
    auto_assign_mode: str = "manual"  # 'manual', 'every_scrape', 'custom'
    custom_interval_minutes: int = 60

class IMAPTestModel(BaseModel):
    server: str
    port: int = 993
    email: str
    password: str
    use_ssl: bool = True
    gmail_label: str = "ConEd"
    subject_filter: str = "Payment Confirmation"

@app.get("/api/imap-config")
async def get_imap_config():
    """Get IMAP configuration (password masked)"""
    from imap_client import load_imap_config
    config = load_imap_config()
    # Mask password
    if config.get('password'):
        config['password'] = '••••••••'
    return config

@app.post("/api/imap-config")
async def save_imap_config_endpoint(config: IMAPConfigModel):
    """Save IMAP configuration"""
    from imap_client import save_imap_config, load_imap_config
    
    # If password is masked, keep existing password
    existing = load_imap_config()
    if config.password == '••••••••' and existing.get('password'):
        password = existing['password']
    else:
        password = config.password
    
    new_config = {
        'enabled': config.enabled,
        'server': config.server,
        'port': config.port,
        'email': config.email,
        'password': password,
        'use_ssl': config.use_ssl,
        'gmail_label': config.gmail_label,
        'subject_filter': config.subject_filter,
        'auto_assign_mode': config.auto_assign_mode,
        'custom_interval_minutes': config.custom_interval_minutes,
        'updated_at': utc_now_iso()
    }
    
    save_imap_config(new_config)
    await db.add_log("info", f"IMAP configuration updated")
    
    return {"success": True, "message": "IMAP configuration saved"}

@app.post("/api/imap-config/test")
async def test_imap_config(config: IMAPTestModel):
    """Test IMAP connection"""
    from imap_client import test_imap_connection, load_imap_config
    
    # If password is masked, use existing password
    password = config.password
    if password == '••••••••':
        existing = load_imap_config()
        password = existing.get('password', '')
    
    # Get gmail_label from existing config if not in test model
    existing = load_imap_config()
    gmail_label = existing.get('gmail_label')
    
    result = test_imap_connection(
        server=config.server,
        port=config.port,
        email_addr=config.email,
        password=password,
        use_ssl=config.use_ssl,
        gmail_label=gmail_label
    )
    
    if result['success']:
        await db.add_log("success", "IMAP connection test successful")
    else:
        await db.add_log("error", f"IMAP connection test failed: {result['message']}")
    
    return result

@app.post("/api/imap-config/preview")
async def preview_imap_emails():
    """Preview emails that would be found with current settings"""
    from imap_client import preview_email_search, load_imap_config
    
    config = load_imap_config()
    
    if not config.get('server') or not config.get('email'):
        return {
            'success': False,
            'message': 'IMAP not configured'
        }
    
    await db.add_log("info", f"Previewing emails - Label: {config.get('gmail_label')}, Subject: {config.get('subject_filter')}")
    
    result = preview_email_search(
        server=config['server'],
        port=config.get('port', 993),
        email_addr=config['email'],
        password=config.get('password', ''),
        use_ssl=config.get('use_ssl', True),
        gmail_label=config.get('gmail_label'),
        subject_filter=config.get('subject_filter'),
        limit=10
    )
    
    if result['success']:
        await db.add_log("success", f"Found {result['emails_found']} payment emails")
    else:
        await db.add_log("error", f"Email preview failed: {result['message']}")
    
    return result

@app.post("/api/imap-config/sync")
async def sync_imap_emails():
    """Run email sync to match payments"""
    from imap_client import run_email_sync
    
    await db.add_log("info", "Starting IMAP email sync...")
    result = run_email_sync()
    
    if result['success']:
        await db.add_log("success", f"Email sync complete: {result['message']}")
    else:
        await db.add_log("error", f"Email sync failed: {result['message']}")
    
    return result

@app.get("/api/imap-config/preview")
async def preview_imap_emails():
    """Preview emails without matching (for debugging)"""
    from imap_client import load_imap_config, fetch_coned_payment_emails
    
    config = load_imap_config()
    
    if not config.get('server'):
        raise HTTPException(status_code=400, detail="IMAP not configured")
    
    try:
        emails = fetch_coned_payment_emails(
            server=config['server'],
            port=config.get('port', 993),
            email_addr=config['email'],
            password=config['password'],
            use_ssl=config.get('use_ssl', True),
            days_back=config.get('days_back', 30)
        )
        
        return {
            "success": True,
            "count": len(emails),
            "emails": emails[:20]  # Limit to 20 for preview
        }
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
    # Using db module for database operations
    
    config = await db.get_meter_config_db() or {
        "enabled": False,
        "email": "",
        "password": "",
        "totp_secret": "",
        "polling_interval": 15
    }
    
    if config.get('password'):
        config['password'] = '••••••••'
    
    return config


@app.post("/api/meter-config")
async def save_meter_config_endpoint(config: MeterConfigModel):
    """Save meter tracking configuration"""
    # Using db module for database operations, save_meter_config_db
    from meter_service import get_meter_service
    
    # Load existing config to preserve password if not provided
    existing = await db.get_meter_config_db() or {}
    
    new_config = {
        "enabled": config.enabled,
        "email": config.email.strip(),
        "totp_secret": config.totp_secret.strip(),
        "polling_interval": config.polling_interval,
        "updated_at": utc_now_iso()
    }
    
    # Handle password - keep existing if masked or empty
    if config.password and config.password != '••••••••':
        new_config['password'] = encrypt_data(config.password)
    elif existing.get('password'):
        new_config['password'] = existing['password']
    else:
        new_config['password'] = ''
    
    await db.save_meter_config_db(new_config)
    
    # Reinitialize meter service with new config
    service = get_meter_service()
    await service.stop_polling()
    
    if new_config['enabled']:
        # Decrypt password for initialization
        init_config = new_config.copy()
        if init_config.get('password'):
            try:
                init_config['password'] = decrypt_data(init_config['password'])
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
    # Using db module for database operations
    from meter_service import get_meter_service

    config = await db.get_meter_config_db()
    if not config:
        raise HTTPException(status_code=400, detail="Meter not configured")

    # Decrypt password
    if config.get('password'):
        try:
            config['password'] = decrypt_data(config['password'])
        except:
            raise HTTPException(status_code=400, detail="Failed to decrypt password")

    service = get_meter_service()
    success = await service.initialize(config)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize meter connection")

    # Get account info first (includes smart meter status)
    account_info = await service.get_account_info()
    
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
        raise HTTPException(status_code=500, detail="Failed to fetch meter reading")


@app.get("/api/meter-reading")
async def get_meter_reading():
    """Get latest meter reading with forecast data - uses cached data for immediate load"""
    from meter_service import get_meter_service
    # Using db module for database operations
    
    service = get_meter_service()
    reading = service.get_cached_reading()
    
    # Get cached forecast for immediate load (no network call)
    forecast = service.get_cached_forecast() if service.is_enabled() else None
    
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
async def get_realtime_usage(hours: int = 24, refresh: bool = False):
    """Get quarter-hour (15-minute) usage data for real-time chart.
    
    Args:
        hours: Number of hours to fetch (default 24, max 144 / 6 days)
        refresh: If True, fetch fresh data from API. If False, use cached data for immediate load.
    
    Returns:
        List of readings with start_time, end_time, consumption
    """
    from meter_service import get_meter_service
    # Using db module for database operations
    
    service = get_meter_service()
    
    if not service.is_enabled():
        raise HTTPException(status_code=400, detail="Meter tracking is not enabled")
    
    # For immediate page load, return cached data first
    if not refresh:
        cached = await db.get_realtime_readings_db()
        if cached:
            return {
                "success": True,
                "readings": cached,
                "hours": 24,
                "count": len(cached),
                "cached": True
            }
    
    # Clamp hours to max 144 (6 days of quarter-hour data)
    hours = min(max(1, hours), 144)
    
    readings = await service.fetch_quarter_hour_reads(hours)
    
    if not readings:
        return {
            "success": True,
            "readings": [],
            "hours": hours,
            "message": "No quarter-hour data available"
        }
    
    return {
        "success": True,
        "readings": readings,
        "hours": hours,
        "count": len(readings),
        "cached": False
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
    # Using db module for database operations
    await db.save_tts_config_db(config)
    # Also write to file for backward compatibility
    try:
        TTS_CONFIG_FILE.write_text(json.dumps(config))
    except:
        pass


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
    """Send test TTS: direct HA API when addon, else MQTT fallback"""
    config = await load_tts_config()
    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="TTS is not enabled")
    media_player = (config.get("media_player") or "").strip()
    if not media_player:
        raise HTTPException(status_code=400, detail="Media player not configured")
    full_msg = f"{config.get('prefix', DEFAULT_TTS_PREFIX)}, Con Edison test message."
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
    return scheduler.load_schedule_config()

@app.post("/api/tts-schedule")
async def save_tts_schedule_endpoint(config: TTSScheduleModel):
    """Save TTS schedule configuration"""
    from tts_scheduler import get_scheduler
    scheduler = get_scheduler()
    current = scheduler.load_schedule_config()
    updates = config.model_dump(exclude_none=True)
    for k, v in updates.items():
        current[k] = v
    scheduler.save_schedule_config(current)
    
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


@app.get("/api/tts/preview-message")
async def preview_tts_message(
    current_sensor: str = None,
    future_sensor: str = None
):
    """Generate preview data for TTS message template variables.
    
    Optional query params allow passing current sensor values from frontend
    (in case they haven't been saved yet).
    """
    from datetime import datetime
    # Using db module for database operations
    from tts_scheduler import get_scheduler

    ledger = await db.get_ledger_data()

    # Get schedule config for sensors - use query params if provided, otherwise use saved config
    scheduler = get_scheduler()
    schedule_config = scheduler.load_schedule_config()
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
            # Try to extract month/day from common formats
            import re
            # Match patterns like "Oct 08, 2025" or "10/08/2025" or "2025-10-08"
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
    # Using db module for database operations_by_id
    last_bill_kwh = ""
    kwh_cost = None
    latest_bill_id = latest_bill.get("id")
    
    if latest_bill_id:
        bill_details = await db.get_bill_details(latest_bill_id)
        if bill_details:
            kwh_val = bill_details.get("kwh_used")
            if kwh_val:
                last_bill_kwh = f"{kwh_val} kWh"
            kwh_cost = bill_details.get("kwh_cost")
            # Use due_date from bill_details if not already set
            if not due_date:
                due_date = format_date_for_tts(bill_details.get("due_date", "") or "")
    
    # Fetch current and future usage from HA sensors
    current_usage_kwh = ""
    current_usage_cost = ""
    projected_usage_kwh = ""
    projected_usage_cost = ""
    
    await db.add_log("debug", f"TTS Preview: current_usage_sensor='{current_usage_sensor}', future_usage_sensor='{future_usage_sensor}'")
    
    token = os.environ.get("SUPERVISOR_TOKEN")
    await db.add_log("debug", f"TTS Preview: SUPERVISOR_TOKEN available={bool(token)}")
    
    if not token:
        await db.add_log("warning", "No SUPERVISOR_TOKEN - cannot fetch sensor states from Home Assistant")
    
    if token and (current_usage_sensor or future_usage_sensor):
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
                            await db.add_log("debug", f"Current usage sensor {sensor_id}: status={resp.status}")
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                unit = state_data.get("attributes", {}).get("unit_of_measurement", "kWh")
                                await db.add_log("debug", f"Current usage state='{sensor_state}', unit={unit}")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        current_usage_kwh = f"{kwh_value:.1f} {unit}"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            current_usage_cost = f"${cost_value:.2f}"
                                        await db.add_log("debug", f"Current usage computed: kwh={current_usage_kwh}, cost={current_usage_cost}")
                                    except ValueError:
                                        current_usage_kwh = f"{sensor_state} {unit}"
                                        await db.add_log("debug", f"Current usage non-numeric: {current_usage_kwh}")
                                else:
                                    await db.add_log("warning", f"Current usage sensor state is '{sensor_state}' - skipping")
                            else:
                                await db.add_log("warning", f"Current usage sensor returned status {resp.status}")
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
                            await db.add_log("debug", f"Future usage sensor {sensor_id}: status={resp.status}")
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                unit = state_data.get("attributes", {}).get("unit_of_measurement", "kWh")
                                await db.add_log("debug", f"Future usage state='{sensor_state}', unit={unit}")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        projected_usage_kwh = f"{kwh_value:.1f} {unit}"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            projected_usage_cost = f"${cost_value:.2f}"
                                        await db.add_log("debug", f"Future usage computed: kwh={projected_usage_kwh}, cost={projected_usage_cost}")
                                    except ValueError:
                                        projected_usage_kwh = f"{sensor_state} {unit}"
                                        await db.add_log("debug", f"Future usage non-numeric: {projected_usage_kwh}")
                                else:
                                    await db.add_log("warning", f"Future usage sensor state is '{sensor_state}' - skipping")
                            else:
                                await db.add_log("warning", f"Future usage sensor returned status {resp.status}")
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
    
    # Log final values before returning
    await db.add_log("debug", f"TTS Preview final: current_usage_kwh='{current_usage_kwh}', current_usage_cost='{current_usage_cost}'")
    await db.add_log("debug", f"TTS Preview final: projected_usage_kwh='{projected_usage_kwh}', projected_usage_cost='{projected_usage_cost}'")
    
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
