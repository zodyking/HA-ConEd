#!/usr/bin/env python3
"""
Standalone runner for Con Edison Python service
"""
import os
import sys
import subprocess
from pathlib import Path

def check_playwright_browsers():
    """Check if Playwright browsers are installed"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to launch chromium to check if it's installed
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except Exception:
        return False

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("Installing Playwright browsers...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Playwright browsers installed successfully")
            return True
        else:
            print(f"✗ Failed to install Playwright browsers: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error installing Playwright browsers: {e}")
        return False

def ensure_data_directory():
    """Ensure data directory exists"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"✓ Data directory ready: {data_dir}")

def main():
    """Main entry point"""
    print("Con Edison - Python Service")
    print("=" * 40)
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Check and install Playwright browsers if needed
    if not check_playwright_browsers():
        print("Playwright browsers not found. Installing...")
        if not install_playwright_browsers():
            print("\n⚠ Warning: Playwright browsers installation failed.")
            print("The service may not work properly. You can install manually with:")
            print("  python -m playwright install chromium")
            print("\nContinuing anyway...")
    else:
        print("✓ Playwright browsers are installed")
    
    # Set environment variables
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PLAYWRIGHT_HEADLESS", "true")
    
    # Import and run uvicorn
    print("\nStarting FastAPI server...")
    print("=" * 40)
    
    import uvicorn
    from main import app
    
    # Get port from environment or default to 8000
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"Server will be available at http://{host}:{port}")
    print(f"API documentation at http://{host}:{port}/docs")
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
