from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
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
from datetime import datetime, timedelta
from database import get_logs, get_latest_scraped_data, get_all_scraped_data, add_log, clear_logs

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
        "updated_at": datetime.now().isoformat()
    }
    SCHEDULE_FILE.write_text(json.dumps(schedule))
    add_log("info", f"Schedule saved: enabled={enabled}, frequency={frequency}s")

async def run_scheduled_scrape():
    """Run a scheduled scrape"""
    try:
        credentials = load_credentials()
        if not credentials:
            add_log("warning", "Scheduled scrape skipped: No credentials found")
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
        
        # Send webhook notifications only for changed values
        webhook_client = get_webhook_client()
        if webhook_client and success and scraped_data:
            from webhook_client import has_data_changed
            
            # Get previous scrape data from database
            previous_scrapes = get_latest_scraped_data(2)  # Get last 2 entries
            previous_data = None
            if len(previous_scrapes) > 1:
                previous_data = previous_scrapes[1].get("data", {})
            
            # Check what changed
            changes = has_data_changed(scraped_data, previous_data)
            timestamp = scraped_data.get("timestamp")
            
            # Send account balance if changed
            if changes.get("account_balance") and scraped_data.get("account_balance"):
                await webhook_client.send_account_balance(
                    scraped_data["account_balance"],
                    timestamp
                )
            
            # Extract bill history data
            if scraped_data.get("bill_history"):
                bill_history = scraped_data["bill_history"]
                ledger = bill_history.get("ledger", [])
                
                # Find latest and previous bills, and last payment
                bills = [item for item in ledger if item.get("type") == "bill"]
                payments = [item for item in ledger if item.get("type") == "payment"]
                
                # Send latest bill if changed
                if changes.get("latest_bill") and len(bills) > 0:
                    await webhook_client.send_latest_bill(bills[0], timestamp)
                
                # Send previous bill if changed
                if changes.get("previous_bill") and len(bills) > 1:
                    await webhook_client.send_previous_bill(bills[1], timestamp)
                
                # Send last payment if changed
                if changes.get("last_payment") and len(payments) > 0:
                    await webhook_client.send_last_payment(payments[0], timestamp)
        
        add_log("success", f"Scheduled scrape completed: {success}")
    except Exception as e:
        error_msg = f"Scheduled scrape failed: {str(e)}"
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
        "updated_at": datetime.now().isoformat()
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
    from browser_automation import perform_login
    from webhook_client import get_webhook_client
    
    credentials = load_credentials()
    if not credentials:
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
        
        # Send webhook notifications only for changed values
        webhook_client = get_webhook_client()
        if webhook_client and success and scraped_data:
            from webhook_client import has_data_changed
            
            # Get previous scrape data from database
            previous_scrapes = get_latest_scraped_data(2)  # Get last 2 entries
            previous_data = None
            if len(previous_scrapes) > 1:
                previous_data = previous_scrapes[1].get("data", {})
            
            # Check what changed
            changes = has_data_changed(scraped_data, previous_data)
            timestamp = scraped_data.get("timestamp")
            
            # Send account balance if changed
            if changes.get("account_balance") and scraped_data.get("account_balance"):
                await webhook_client.send_account_balance(
                    scraped_data["account_balance"],
                    timestamp
                )
            
            # Extract bill history data
            if scraped_data.get("bill_history"):
                bill_history = scraped_data["bill_history"]
                ledger = bill_history.get("ledger", [])
                
                # Find latest and previous bills, and last payment
                bills = [item for item in ledger if item.get("type") == "bill"]
                payments = [item for item in ledger if item.get("type") == "payment"]
                
                # Send latest bill if changed
                if changes.get("latest_bill") and len(bills) > 0:
                    await webhook_client.send_latest_bill(bills[0], timestamp)
                
                # Send previous bill if changed
                if changes.get("previous_bill") and len(bills) > 1:
                    await webhook_client.send_previous_bill(bills[1], timestamp)
                
                # Send last payment if changed
                if changes.get("last_payment") and len(payments) > 0:
                    await webhook_client.send_last_payment(payments[0], timestamp)
        
        add_log("success", f"Scraper completed: {success}")
        return result
    except Exception as e:
        error_msg = str(e)
        add_log("error", f"Scraper failed: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
