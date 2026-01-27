from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
from database import (
    get_logs, get_latest_scraped_data, get_all_scraped_data, add_log, clear_logs, 
    add_scrape_history, get_scrape_history,
    # New normalized data functions
    get_ledger_data, get_all_bills, get_all_payments, get_latest_payment,
    get_payee_users, create_payee_user, update_payee_user, delete_payee_user,
    add_user_card, delete_user_card, get_user_by_card,
    attribute_payment, get_unverified_payments, clear_payment_attribution,
    wipe_bills_and_payments, update_payment_bill, get_payment_by_id,
    update_payment_order, get_payments_by_user, get_all_bills_with_payments,
    update_payee_responsibilities, get_bill_payee_summary
)

app = FastAPI(title="ConEd Scraper API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (safe in containerized environment)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
# Use ./data for persistent storage (works in both Docker and local)
DATA_DIR = Path("./data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_FILE = DATA_DIR / "credentials.json"
WEBHOOKS_FILE = DATA_DIR / "webhooks.json"
MQTT_CONFIG_FILE = DATA_DIR / "mqtt_config.json"
SETTINGS_FILE = DATA_DIR / "app_settings.json"
IMAP_CONFIG_FILE = DATA_DIR / "imap_config.json"
KEY_FILE = DATA_DIR / ".key"

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

class ScheduleModel(BaseModel):
    enabled: bool
    frequency: int  # Frequency in seconds

def load_schedule() -> dict:
    """Load automated scraping schedule"""
    if not SCHEDULE_FILE.exists():
        return {"enabled": False, "frequency": 3600}  # Default: disabled, 1 hour
    
    try:
        data = json.loads(SCHEDULE_FILE.read_text())
        return {
            "enabled": data.get("enabled", False),
            "frequency": data.get("frequency", 3600)
        }
    except Exception as e:
        add_log("error", f"Failed to load schedule: {str(e)}")
        return {"enabled": False, "frequency": 3600}

def save_schedule(enabled: bool, frequency: int):
    """Save automated scraping schedule"""
    schedule = {
        "enabled": enabled,
        "frequency": frequency,
        "updated_at": utc_now_iso()
    }
    SCHEDULE_FILE.write_text(json.dumps(schedule))
    add_log("info", f"Schedule saved: enabled={enabled}, frequency={frequency}s")

async def run_scheduled_scrape():
    """Run a scheduled scrape"""
    import time as time_module
    start_time = time_module.time()
    
    try:
        credentials = load_credentials()
        if not credentials:
            add_log("warning", "Scheduled scrape skipped: No credentials found")
            add_scrape_history(False, "No credentials found", "credentials_check", 0)
            return
        
        from browser_automation import perform_login
        from webhook_client import get_webhook_client
        
        username = credentials["username"]
        password = credentials["password"]
        totp = pyotp.TOTP(credentials["totp_secret"])
        totp_code = totp.now()
        
        add_log("info", "Starting scheduled scrape...")
        result = await perform_login(username, password, totp_code)
        success = result.get('success', False)
        scraped_data = result.get('data', {})
        
        # Send notifications: Webhooks only on changes, MQTT always publishes
        webhook_client = get_webhook_client()
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
                    payments = [item for item in ledger if item.get("type") == "payment"]
                    
                    if len(bills) > 0:
                        await mqtt_client.publish_latest_bill(bills[0], timestamp)
                    if len(bills) >= 2:
                        await mqtt_client.publish_previous_bill(bills[1], timestamp)
                    if len(payments) > 0:
                        await mqtt_client.publish_last_payment(payments[0], timestamp)
            
            # Webhooks: Only send for changed values
            if webhook_client:
                from webhook_client import has_data_changed
                
                # Get previous scrape data from database
                previous_scrapes = get_latest_scraped_data(2)  # Get last 2 entries
                previous_data = None
                if len(previous_scrapes) > 1:
                    previous_data = previous_scrapes[1].get("data", {})
                
                # Check what changed
                changes = has_data_changed(scraped_data, previous_data)
                
                # Send account balance if changed
                if changes.get("account_balance") and scraped_data.get("account_balance"):
                    await webhook_client.send_account_balance(scraped_data["account_balance"], timestamp)
                
                # Extract bill history data
                if scraped_data.get("bill_history"):
                    bill_history = scraped_data["bill_history"]
                    ledger = bill_history.get("ledger", [])
                    bills = [item for item in ledger if item.get("type") == "bill"]
                    payments = [item for item in ledger if item.get("type") == "payment"]
                    
                    # Send latest bill if changed
                    if changes.get("latest_bill") and len(bills) > 0:
                        await webhook_client.send_latest_bill(bills[0], timestamp)
                    
                    # Send previous bill if changed
                    if changes.get("previous_bill") and len(bills) >= 2:
                        await webhook_client.send_previous_bill(bills[1], timestamp)
                    
                    # Send last payment if changed
                    if changes.get("last_payment") and len(payments) > 0:
                        await webhook_client.send_last_payment(payments[0], timestamp)
        
        duration = time_module.time() - start_time
        add_scrape_history(success, None if success else "Scrape failed", None, duration)
        add_log("success", f"Scheduled scrape completed: {success}")
    except Exception as e:
        duration = time_module.time() - start_time
        error_msg = f"Scheduled scrape failed: {str(e)}"
        add_scrape_history(False, error_msg, "unknown", duration)
        add_log("error", error_msg)
        logging.error(error_msg)

async def scheduler_loop():
    """Background scheduler loop"""
    while True:
        try:
            schedule = load_schedule()
            
            if schedule["enabled"]:
                frequency = schedule["frequency"]
                add_log("info", f"Scheduler: Waiting {frequency} seconds until next scrape...")
                await asyncio.sleep(frequency)
                
                # Check if still enabled before running
                current_schedule = load_schedule()
                if current_schedule["enabled"]:
                    await run_scheduled_scrape()
            else:
                # If disabled, check every 60 seconds
                await asyncio.sleep(60)
        except Exception as e:
            error_msg = f"Scheduler error: {str(e)}"
            add_log("error", error_msg)
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
        add_log("info", "Scheduler restarted")
    else:
        add_log("info", "Scheduler disabled")

# Start scheduler on app startup
@app.on_event("startup")
async def startup_event():
    global _scheduler_task
    
    # Initialize webhook client from saved configuration
    try:
        from webhook_client import init_webhook_client
        saved_config = load_webhook_config()
        init_webhook_client(saved_config)
        configured_count = sum(1 for v in saved_config.values() if v)
        add_log("info", f"Webhook client initialized with {configured_count} webhook(s)")
    except Exception as e:
        add_log("warning", f"Webhook initialization failed: {e}")
    
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
                mqtt_config.get("mqtt_retain", True)
            )
            add_log("info", "MQTT client initialized")
    except Exception as e:
        add_log("warning", f"MQTT initialization failed: {e}")
    
    schedule = load_schedule()
    if schedule["enabled"]:
        _scheduler_task = asyncio.create_task(scheduler_loop())
        add_log("info", f"Scheduler started with {schedule['frequency']}s frequency")

@app.on_event("shutdown")
async def shutdown_event():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

class CredentialsModel(BaseModel):
    username: str
    password: Optional[str] = None
    totp_secret: str

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    totp_code: Optional[str] = None

class WebhookConfigModel(BaseModel):
    latest_bill: str = ""
    previous_bill: str = ""
    account_balance: str = ""
    last_payment: str = ""

class MQTTConfigModel(BaseModel):
    mqtt_url: str = ""
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_base_topic: str = "coned"
    mqtt_qos: int = 1
    mqtt_retain: bool = True

class AppSettingsModel(BaseModel):
    time_offset_hours: float = 0.0
    settings_password: str = "0000"
    app_base_url: str = ""  # e.g., https://coned.brandon-built.com

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

def save_webhook_config(webhook_config: dict):
    """Save webhook configuration to file"""
    webhook_data = {
        "latest_bill": webhook_config.get("latest_bill", ""),
        "previous_bill": webhook_config.get("previous_bill", ""),
        "account_balance": webhook_config.get("account_balance", ""),
        "last_payment": webhook_config.get("last_payment", ""),
        "updated_at": utc_now_iso()
    }
    WEBHOOKS_FILE.write_text(json.dumps(webhook_data))

def load_webhook_config() -> dict:
    """Load webhook configuration from file"""
    if not WEBHOOKS_FILE.exists():
        return {}
    
    try:
        data = json.loads(WEBHOOKS_FILE.read_text())
        return {
            "latest_bill": data.get("latest_bill", ""),
            "previous_bill": data.get("previous_bill", ""),
            "account_balance": data.get("account_balance", ""),
            "last_payment": data.get("last_payment", "")
        }
    except Exception as e:
        add_log("warning", f"Failed to load webhooks: {str(e)}")
        return {}

def save_mqtt_config(mqtt_config: dict):
    """Save MQTT configuration to file"""
    config_data = {
        "mqtt_url": mqtt_config.get("mqtt_url", ""),
        "mqtt_username": mqtt_config.get("mqtt_username", ""),
        "mqtt_password": encrypt_data(mqtt_config.get("mqtt_password", "")),  # Encrypt password
        "mqtt_base_topic": mqtt_config.get("mqtt_base_topic", "coned"),
        "mqtt_qos": mqtt_config.get("mqtt_qos", 1),
        "mqtt_retain": mqtt_config.get("mqtt_retain", True),
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
            "mqtt_retain": data.get("mqtt_retain", True)
        }
    except Exception as e:
        add_log("warning", f"Failed to load MQTT config: {str(e)}")
        return {}

def save_app_settings(settings: dict):
    """Save app settings (time offset, password, base URL) to file"""
    settings_data = {
        "time_offset_hours": float(settings.get("time_offset_hours", 0.0)),
        "settings_password": encrypt_data(settings.get("settings_password", "0000")),
        "app_base_url": settings.get("app_base_url", ""),
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
            "app_base_url": ""
        }
        save_app_settings(default_settings)
        return default_settings
    
    try:
        data = json.loads(SETTINGS_FILE.read_text())
        return {
            "time_offset_hours": float(data.get("time_offset_hours", 0.0)),
            "settings_password": decrypt_data(data.get("settings_password", encrypt_data("0000"))) if data.get("settings_password") else "0000",
            "app_base_url": data.get("app_base_url", "")
        }
    except Exception as e:
        add_log("warning", f"Failed to load app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "settings_password": "0000", "app_base_url": ""}

def verify_settings_password(password: str) -> bool:
    """Verify settings password"""
    settings = load_app_settings()
    return settings.get("settings_password") == password

@app.get("/")
async def root():
    return {"message": "ConEd Scraper API", "status": "running"}

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
        add_log("error", error_detail)
        raise HTTPException(status_code=500, detail=f"Failed to generate TOTP: {str(e)}")

@app.post("/api/webhooks")
async def configure_webhooks(config: WebhookConfigModel):
    """Configure webhook URLs"""
    try:
        from webhook_client import init_webhook_client
        
        # Build webhook config dict
        webhook_config = {
            "latest_bill": config.latest_bill.strip(),
            "previous_bill": config.previous_bill.strip(),
            "account_balance": config.account_balance.strip(),
            "last_payment": config.last_payment.strip()
        }
        
        # Save to file for persistence
        save_webhook_config(webhook_config)
        
        # Initialize webhook client with new config
        init_webhook_client(webhook_config)
        
        configured_count = sum(1 for v in webhook_config.values() if v)
        add_log("success", f"Webhooks configured: {configured_count} webhook(s)")
        return {
            "message": "Webhooks configured successfully",
            "configured_count": configured_count
        }
    except Exception as e:
        error_msg = f"Failed to configure webhooks: {str(e)}"
        add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/webhooks")
async def get_webhook_config():
    """Get current webhook configuration"""
    try:
        from webhook_client import get_webhook_client
        
        webhook_client = get_webhook_client()
        if webhook_client and webhook_client.webhook_config:
            return webhook_client.webhook_config
        else:
            # Try loading from file as fallback
            saved_config = load_webhook_config()
            if saved_config:
                return saved_config
            else:
                return {
                    "latest_bill": "",
                    "previous_bill": "",
                    "account_balance": "",
                    "last_payment": ""
                }
    except Exception as e:
        add_log("error", f"Failed to get webhook config: {str(e)}")
        return {
            "latest_bill": "",
            "previous_bill": "",
            "account_balance": "",
            "last_payment": ""
        }

@app.post("/api/webhooks/test")
async def test_webhooks():
    """Test webhooks by sending the latest scraped data (forces send regardless of changes)"""
    try:
        from webhook_client import get_webhook_client
        
        webhook_client = get_webhook_client()
        if not webhook_client or not any(webhook_client.webhook_config.values()):
            raise HTTPException(status_code=400, detail="No webhooks configured")
        
        # Get latest scraped data
        latest_data = get_latest_scraped_data(1)
        if not latest_data or latest_data[0].get("status") != "success":
            raise HTTPException(status_code=404, detail="No successful scrape data available. Run a scrape first.")
        
        scraped_data = latest_data[0].get("data", {})
        timestamp = latest_data[0].get("timestamp")
        
        # Send webhooks with existing data (force send for testing)
        webhooks_sent = []
        
        if scraped_data.get("account_balance"):
            await webhook_client.send_account_balance(
                scraped_data["account_balance"],
                timestamp
            )
            webhooks_sent.append("account_balance")
        
        if scraped_data.get("bill_history"):
            bill_history = scraped_data["bill_history"]
            ledger = bill_history.get("ledger", [])
            
            bills = [item for item in ledger if item.get("type") == "bill"]
            payments = [item for item in ledger if item.get("type") == "payment"]
            
            if len(bills) > 0:
                await webhook_client.send_latest_bill(bills[0], timestamp)
                webhooks_sent.append("latest_bill")
            
            if len(bills) > 1:
                await webhook_client.send_previous_bill(bills[1], timestamp)
                webhooks_sent.append("previous_bill")
            
            if len(payments) > 0:
                await webhook_client.send_last_payment(payments[0], timestamp)
                webhooks_sent.append("last_payment")
        
        if webhooks_sent:
            add_log("success", f"Test webhooks sent: {', '.join(webhooks_sent)}")
            return {
                "message": "Test webhooks sent successfully",
                "webhooks_sent": webhooks_sent
            }
        else:
            return {
                "message": "No webhooks sent - no data available or no webhooks configured"
            }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to test webhooks: {str(e)}"
        add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

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
            add_log("info", f"TOTP secret validated successfully, test code: {test_code}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid TOTP secret format: {str(e)}")
        
        # If password is not provided, use existing password
        if credentials.password is None or credentials.password == "":
            existing_creds = load_credentials()
            if existing_creds:
                password = existing_creds["password"]
                add_log("info", "Using existing password")
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
        
        add_log("success", "Credentials saved successfully")
        return {"message": "Credentials saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to save settings: {str(e)}"
        add_log("error", error_msg)
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
        add_log("error", f"Failed to get settings: {str(e)}")
        return {"username": "", "password": "", "totp_secret": ""}

@app.post("/api/scrape")
async def start_scraper():
    """Start scraper automation"""
    import time as time_module
    start_time = time_module.time()
    
    from browser_automation import perform_login
    from webhook_client import get_webhook_client
    
    credentials = load_credentials()
    if not credentials:
        add_scrape_history(False, "No credentials found", "credentials_check", 0)
        raise HTTPException(status_code=404, detail="No credentials found. Please configure settings first.")
    
    # Clear previous logs when starting a new scrape
    clear_logs()
    add_log("info", "Scraper started by user")
    
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
        
        # Send notifications: Webhooks only on changes, MQTT always publishes
        webhook_client = get_webhook_client()
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
                    payments = [item for item in ledger if item.get("type") == "payment"]
                    
                    if len(bills) > 0:
                        await mqtt_client.publish_latest_bill(bills[0], timestamp)
                    if len(bills) >= 2:
                        await mqtt_client.publish_previous_bill(bills[1], timestamp)
                    if len(payments) > 0:
                        await mqtt_client.publish_last_payment(payments[0], timestamp)
            
            # Webhooks: Only send for changed values
            if webhook_client:
                from webhook_client import has_data_changed
                
                # Get previous scrape data from database
                previous_scrapes = get_latest_scraped_data(2)  # Get last 2 entries
                previous_data = None
                if len(previous_scrapes) > 1:
                    previous_data = previous_scrapes[1].get("data", {})
                
                # Check what changed
                changes = has_data_changed(scraped_data, previous_data)
                
                # Send account balance if changed
                if changes.get("account_balance") and scraped_data.get("account_balance"):
                    await webhook_client.send_account_balance(scraped_data["account_balance"], timestamp)
                
                # Extract bill history data
                if scraped_data.get("bill_history"):
                    bill_history = scraped_data["bill_history"]
                    ledger = bill_history.get("ledger", [])
                    bills = [item for item in ledger if item.get("type") == "bill"]
                    payments = [item for item in ledger if item.get("type") == "payment"]
                    
                    # Send latest bill if changed
                    if changes.get("latest_bill") and len(bills) > 0:
                        await webhook_client.send_latest_bill(bills[0], timestamp)
                    
                    # Send previous bill if changed
                    if changes.get("previous_bill") and len(bills) >= 2:
                        await webhook_client.send_previous_bill(bills[1], timestamp)
                    
                    # Send last payment if changed
                    if changes.get("last_payment") and len(payments) > 0:
                        await webhook_client.send_last_payment(payments[0], timestamp)
        
        duration = time_module.time() - start_time
        add_scrape_history(success, None if success else "Scrape failed", None, duration)
        add_log("success", f"Scraper completed: {success}")
        return result
    except Exception as e:
        duration = time_module.time() - start_time
        error_msg = str(e)
        add_scrape_history(False, error_msg, "unknown", duration)
        add_log("error", f"Scraper failed: {error_msg}")
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
            "mqtt_retain": config.mqtt_retain
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
                mqtt_config["mqtt_retain"]
            )
            add_log("success", "MQTT configured successfully")
        else:
            add_log("info", "MQTT disabled (no URL provided)")
        
        return {"message": "MQTT configured successfully"}
    except Exception as e:
        error_msg = f"Failed to configure MQTT: {str(e)}"
        add_log("error", error_msg)
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
            "mqtt_retain": mqtt_config.get("mqtt_retain", True)
        }
    except Exception as e:
        add_log("error", f"Failed to get MQTT config: {str(e)}")
        return {
            "mqtt_url": "",
            "mqtt_username": "",
            "mqtt_password": "",
            "mqtt_base_topic": "coned",
            "mqtt_qos": 1,
            "mqtt_retain": True
        }

@app.post("/api/app-settings")
async def save_app_settings_endpoint(settings: AppSettingsModel):
    """Save app settings (time offset, password, base URL)"""
    try:
        settings_dict = {
            "time_offset_hours": settings.time_offset_hours,
            "settings_password": settings.settings_password.strip() if settings.settings_password else "0000",
            "app_base_url": settings.app_base_url.strip().rstrip('/') if settings.app_base_url else ""
        }
        save_app_settings(settings_dict)
        add_log("success", "App settings saved successfully")
        return {"message": "Settings saved successfully"}
    except Exception as e:
        error_msg = f"Failed to save app settings: {str(e)}"
        add_log("error", error_msg)
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
            "app_base_url": settings.get("app_base_url", "")
        }
    except Exception as e:
        add_log("error", f"Failed to get app settings: {str(e)}")
        return {"time_offset_hours": 0.0, "has_password": True, "settings_password": "0000", "app_base_url": ""}

class PasswordVerifyModel(BaseModel):
    password: str

@app.post("/api/app-settings/verify-password")
async def verify_password_endpoint(data: PasswordVerifyModel):
    """Verify settings password"""
    try:
        is_valid = verify_settings_password(data.password)
        return {"valid": is_valid}
    except Exception as e:
        add_log("error", f"Failed to verify password: {str(e)}")
        return {"valid": False}

@app.get("/api/logs")
async def get_logs_endpoint(limit: int = 100):
    """Get log entries"""
    logs = get_logs(limit)
    return {"logs": logs}

@app.delete("/api/logs")
async def clear_logs_endpoint():
    """Clear all log entries"""
    clear_logs()
    return {"message": "Logs cleared successfully"}

@app.get("/api/scrape-history")
async def get_scrape_history_endpoint(limit: int = 50):
    """Get scrape history"""
    history = get_scrape_history(limit)
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

@app.get("/api/bill-document")
async def get_bill_document():
    """Get the latest bill PDF (alt endpoint to avoid ad blockers)"""
    return await get_latest_bill_pdf()

@app.get("/api/latest-bill-pdf")
async def get_latest_bill_pdf():
    """Get the latest bill PDF (downloaded and stored locally)"""
    import os
    from fastapi.responses import FileResponse, JSONResponse, Response
    
    pdf_path = DATA_DIR / "latest_bill.pdf"
    
    if os.path.exists(pdf_path):
        # Read the file and return with proper headers for iframe embedding
        with open(pdf_path, 'rb') as f:
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
    else:
        return JSONResponse(
            {"error": "No bill PDF available. Add a PDF link in Settings."},
            status_code=404
        )

@app.get("/api/latest-bill-pdf/status")
async def get_pdf_status():
    """Check if a bill PDF exists"""
    import os
    pdf_path = DATA_DIR / "latest_bill.pdf"
    exists = os.path.exists(pdf_path)
    size = os.path.getsize(pdf_path) if exists else 0
    readable = False
    if exists:
        try:
            with open(pdf_path, 'rb') as f:
                first_bytes = f.read(10)
                readable = len(first_bytes) > 0
        except:
            readable = False
    return {
        "exists": exists,
        "size_bytes": size,
        "size_kb": round(size / 1024, 1) if size else 0,
        "readable": readable,
        "path": str(pdf_path)
    }

class PdfDownloadRequest(BaseModel):
    url: str

@app.post("/api/latest-bill-pdf/download")
async def download_bill_pdf(request: PdfDownloadRequest):
    """Download a bill PDF from provided URL and store locally"""
    import aiohttp
    import os
    from mqtt_client import get_mqtt_client
    
    pdf_url = request.url.strip()
    
    if not pdf_url:
        raise HTTPException(status_code=400, detail="PDF URL is required")
    
    # Validate URL looks like a PDF
    if not ('blob.core.windows.net' in pdf_url or '.pdf' in pdf_url.lower() or 'cecony' in pdf_url.lower()):
        add_log("warning", f"URL doesn't look like a ConEd PDF: {pdf_url[:50]}...")
    
    try:
        add_log("info", f"Downloading PDF from: {pdf_url[:80]}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    pdf_content = await response.read()
                    
                    if len(pdf_content) < 1000:
                        add_log("error", f"PDF content too small: {len(pdf_content)} bytes")
                        raise HTTPException(status_code=400, detail="Downloaded file is too small to be a valid PDF")
                    
                    # Delete old PDF if exists
                    pdf_path = DATA_DIR / "latest_bill.pdf"
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        add_log("info", "Deleted old PDF")
                    
                    # Save new PDF
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    size_kb = round(len(pdf_content) / 1024, 1)
                    add_log("success", f"PDF saved: {size_kb} KB")
                    
                    # Publish PDF URL to MQTT
                    mqtt_client = get_mqtt_client()
                    if mqtt_client:
                        # Get the app's public URL for the PDF
                        app_settings = load_app_settings()
                        base_url = app_settings.get("app_base_url", "").rstrip("/")
                        if base_url:
                            hosted_pdf_url = f"{base_url}/api/latest-bill-pdf"
                            await mqtt_client.publish_bill_pdf_url(hosted_pdf_url, utc_now_iso())
                            add_log("info", f"Published PDF URL to MQTT: {hosted_pdf_url}")
                        else:
                            add_log("warning", "App Base URL not configured, skipping MQTT publish for PDF")
                    
                    return {
                        "success": True,
                        "message": f"PDF downloaded successfully ({size_kb} KB)",
                        "size_bytes": len(pdf_content)
                    }
                else:
                    add_log("error", f"PDF download failed: HTTP {response.status}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to download PDF: HTTP {response.status}. The link may have expired."
                    )
                    
    except aiohttp.ClientError as e:
        add_log("error", f"PDF download error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")
    except Exception as e:
        add_log("error", f"PDF download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/api/latest-bill-pdf/send-mqtt")
async def send_pdf_url_mqtt():
    """Manually send the PDF URL to Home Assistant via MQTT"""
    import os
    from mqtt_client import get_mqtt_client
    
    pdf_path = DATA_DIR / "latest_bill.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="No PDF available to send")
    
    try:
        app_settings = load_app_settings()
        base_url = app_settings.get("app_base_url", "").rstrip("/")
        
        if not base_url:
            raise HTTPException(status_code=400, detail="App Base URL not configured. Set it in Settings to send PDF URL via MQTT.")
        
        mqtt_client = get_mqtt_client()
        if not mqtt_client:
            raise HTTPException(status_code=400, detail="MQTT client not available")
        
        hosted_pdf_url = f"{base_url}/api/bill-document"
        await mqtt_client.publish_bill_pdf_url(hosted_pdf_url, utc_now_iso())
        add_log("info", f"Manually sent PDF URL to MQTT: {hosted_pdf_url}")
        
        return {"success": True, "message": f"PDF URL sent to MQTT: {hosted_pdf_url}"}
        
    except HTTPException:
        raise
    except Exception as e:
        add_log("error", f"Failed to send PDF URL via MQTT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")

@app.delete("/api/latest-bill-pdf")
async def delete_bill_pdf():
    """Delete the stored bill PDF"""
    import os
    pdf_path = DATA_DIR / "latest_bill.pdf"
    
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        add_log("info", "Bill PDF deleted")
        return {"success": True, "message": "PDF deleted"}
    else:
        return {"success": True, "message": "No PDF to delete"}

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
    schedule = load_schedule()
    
    # Calculate next run time if enabled
    next_run = None
    if schedule["enabled"]:
        # Try to get last run time from logs or use now
        next_run = (datetime.now() + timedelta(seconds=schedule["frequency"])).isoformat()
    
    return {
        "enabled": schedule["enabled"],
        "frequency": schedule["frequency"],
        "nextRun": next_run
    }

@app.post("/api/automated-schedule")
async def save_automated_schedule(schedule: ScheduleModel):
    """Save automated scraping schedule"""
    try:
        if schedule.frequency <= 0:
            raise HTTPException(status_code=400, detail="Frequency must be greater than 0")
        
        save_schedule(schedule.enabled, schedule.frequency)
        
        # Restart scheduler with new settings
        await restart_scheduler()
        
        # Calculate next run time
        next_run = None
        if schedule.enabled:
            next_run = (datetime.now() + timedelta(seconds=schedule.frequency)).isoformat()
        
        return {
            "enabled": schedule.enabled,
            "frequency": schedule.frequency,
            "nextRun": next_run,
            "message": "Schedule saved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to save schedule: {str(e)}"
        add_log("error", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# ==========================================
# LEDGER API ENDPOINTS (Database-driven)
# ==========================================

@app.get("/api/ledger")
async def get_ledger():
    """Get complete ledger data from normalized database tables"""
    try:
        data = get_ledger_data()
        return data
    except Exception as e:
        add_log("error", f"Failed to get ledger: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills")
async def get_bills(limit: int = 50):
    """Get all bills from database"""
    try:
        bills = get_all_bills(limit)
        return {"bills": bills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments")
async def get_payments(limit: int = 100, bill_id: Optional[int] = None):
    """Get all payments from database"""
    try:
        payments = get_all_payments(limit, bill_id)
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments/unverified")
async def get_payments_unverified(limit: int = 50):
    """Get payments that need payee verification"""
    try:
        payments = get_unverified_payments(limit)
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
        users = get_payee_users()
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payee-users")
async def create_user(user: PayeeUserModel):
    """Create a new payee user"""
    try:
        user_id = create_payee_user(user.name, user.is_default)
        add_log("info", f"Created payee user: {user.name}")
        return {"id": user_id, "name": user.name, "is_default": user.is_default}
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=400, detail="User with this name already exists")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/payee-users/{user_id}")
async def update_user(user_id: int, user: PayeeUserUpdateModel):
    """Update a payee user"""
    try:
        update_payee_user(user_id, user.name, user.is_default)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/payee-users/{user_id}")
async def delete_user(user_id: int):
    """Delete a payee user"""
    try:
        deleted = delete_payee_user(user_id)
        if deleted:
            add_log("info", f"Deleted payee user ID: {user_id}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ResponsibilitiesModel(BaseModel):
    responsibilities: Dict[str, Any]  # {user_id: percent}

@app.put("/api/payee-users/responsibilities")
async def update_responsibilities(data: ResponsibilitiesModel):
    """Update bill responsibility percentages for payees (must total 100%)"""
    try:
        # Convert string keys to int
        responsibilities = {int(k): float(v) for k, v in data.responsibilities.items()}
        result = update_payee_responsibilities(responsibilities)
        if result['success']:
            add_log("info", f"Updated payee responsibilities: {result['total']}% total")
            return result
        raise HTTPException(status_code=400, detail=result.get('error', 'Invalid percentages'))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills/{bill_id}/summary")
async def get_bill_summary(bill_id: int):
    """Get payee payment summary for a specific bill"""
    try:
        summary = get_bill_payee_summary(bill_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user-cards")
async def add_card(card: UserCardModel):
    """Add a card to a user"""
    try:
        card_id = add_user_card(card.user_id, card.card_last_four, card.label)
        add_log("info", f"Added card *{card.card_last_four} to user ID: {card.user_id}")
        return {"id": card_id}
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=400, detail="This card ending is already registered")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/user-cards/{card_id}")
async def remove_card(card_id: int):
    """Remove a card"""
    try:
        deleted = delete_user_card(card_id)
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
        success = attribute_payment(attribution.payment_id, attribution.user_id, attribution.method)
        if success:
            add_log("info", f"Attributed payment {attribution.payment_id} to user {attribution.user_id}")
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
        success = clear_payment_attribution(payment_id)
        if success:
            add_log("info", f"Cleared attribution for payment {payment_id}")
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
        payment = get_payment_by_id(payment_id)
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
        success = update_payment_bill(payment_id, data.bill_id, manual=True)
        if success:
            add_log("info", f"Manually assigned payment {payment_id} to bill {data.bill_id}")
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
        result = wipe_bills_and_payments()
        add_log("warning", f"Database wiped: {result['bills_deleted']} bills, {result['payments_deleted']} payments deleted")
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
        success = update_payment_order(payment_id, data.bill_id, data.order)
        if success:
            add_log("info", f"Manually set payment {payment_id} to bill {data.bill_id} at position {data.order}")
            return {"success": True}
        raise HTTPException(status_code=404, detail="Payment not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payee-users/{user_id}/payments")
async def get_user_payments(user_id: int):
    """Get all payments assigned to a specific user"""
    try:
        payments = get_payments_by_user(user_id)
        return {"payments": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bills-with-payments")
async def get_bills_with_payments_endpoint():
    """Get all bills with their payments for the audit tab"""
    try:
        data = get_all_bills_with_payments()
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
    add_log("info", f"IMAP configuration updated")
    
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
        add_log("success", "IMAP connection test successful")
    else:
        add_log("error", f"IMAP connection test failed: {result['message']}")
    
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
    
    add_log("info", f"Previewing emails - Label: {config.get('gmail_label')}, Subject: {config.get('subject_filter')}")
    
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
        add_log("success", f"Found {result['emails_found']} payment emails")
    else:
        add_log("error", f"Email preview failed: {result['message']}")
    
    return result

@app.post("/api/imap-config/sync")
async def sync_imap_emails():
    """Run email sync to match payments"""
    from imap_client import run_email_sync
    
    add_log("info", "Starting IMAP email sync...")
    result = run_email_sync()
    
    if result['success']:
        add_log("success", f"Email sync complete: {result['message']}")
    else:
        add_log("error", f"Email sync failed: {result['message']}")
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
