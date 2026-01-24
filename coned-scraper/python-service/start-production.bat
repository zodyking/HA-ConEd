@echo off
REM Production startup script for ConEd Scraper Python Service
REM This runs the FastAPI server with production settings

echo ========================================
echo ConEd Scraper - Production Server
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo.
echo Checking dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Create data directory if it doesn't exist
if not exist "data" mkdir data

REM Set environment variables for production
set PLAYWRIGHT_HEADLESS=true
set PYTHONUNBUFFERED=1

echo.
echo ========================================
echo Starting Production Server
echo ========================================
echo API will be available at: http://localhost:8000
echo Scheduler: Runs in background (if enabled in settings)
echo Headless Mode: Enabled (no browser window)
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the FastAPI server with uvicorn in production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

REM If the server stops, pause to see any error messages
pause
