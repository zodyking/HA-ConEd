@echo off
REM ConEd Scraper Python Service - Windows Runner
echo ConEd Scraper - Python Service
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please run this script from the python-service directory
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if Playwright browsers are installed
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo Installing Playwright browsers...
    python -m playwright install chromium
    if errorlevel 1 (
        echo WARNING: Failed to install Playwright browsers
        echo The service may not work properly
    )
)

REM Create data directory
if not exist "data" mkdir data

REM Set environment variables
set PYTHONUNBUFFERED=1
set PLAYWRIGHT_HEADLESS=true

REM Run the service
echo.
echo Starting FastAPI server...
echo ========================================
echo Server will be available at http://localhost:8000
echo API documentation at http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python run.py

pause
