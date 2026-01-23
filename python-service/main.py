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
from database import get_logs, get_latest_scraped_data, get_all_scraped_data, add_log

app = FastAPI(title="ConEd Scraper API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_FILE = DATA_DIR / "credentials.json"
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

class CredentialsModel(BaseModel):
    username: str
    password: Optional[str] = None
    totp_secret: str

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    totp_code: Optional[str] = None

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
    
    credentials = load_credentials()
    if not credentials:
        raise HTTPException(status_code=404, detail="No credentials found. Please configure settings first.")
    
    add_log("info", "Scraper started by user")
    
    # Use saved credentials
    username = credentials["username"]
    password = credentials["password"]
    
    # Generate TOTP code
    totp = pyotp.TOTP(credentials["totp_secret"])
    totp_code = totp.now()
    
    try:
        result = await perform_login(username, password, totp_code)
        add_log("success", f"Scraper completed: {result.get('success', False)}")
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

@app.get("/api/screenshot/latest")
async def get_latest_screenshot():
    """Get latest browser screenshot for live preview"""
    import os
    from pathlib import Path
    from browser_automation import SCREENSHOT_FILENAME
    
    # Always use the single screenshot filename
    screenshot_path = Path(__file__).parent / SCREENSHOT_FILENAME
    
    if os.path.exists(screenshot_path):
        from fastapi.responses import FileResponse
        # Add cache busting headers
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
        # Return 404 with proper JSON
        from fastapi.responses import JSONResponse
        return JSONResponse(
            {"error": "No screenshot available"}, 
            status_code=404,
            headers={
                "Cache-Control": "no-cache"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
