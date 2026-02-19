#!/bin/bash
# ConEd Scraper Python Service - Linux/Mac Runner

set -e

echo "ConEd Scraper - Python Service"
echo "========================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found"
    echo "Please run this script from the python-service directory"
    exit 1
fi

# Check if requirements are installed
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

# Check if Playwright browsers are installed
if ! python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" &> /dev/null; then
    echo "Installing Playwright browsers..."
    python3 -m playwright install chromium || {
        echo "WARNING: Failed to install Playwright browsers"
        echo "The service may not work properly"
    }
fi

# Create data directory
mkdir -p data

# Set environment variables
export PYTHONUNBUFFERED=1
export PLAYWRIGHT_HEADLESS=true

# Run the service
echo ""
echo "Starting FastAPI server..."
echo "========================================"
echo "Server will be available at http://localhost:8000"
echo "API documentation at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 run.py
