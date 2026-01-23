@echo off
echo ConEd Scraper Setup
echo ===================
echo.

echo [1/3] Installing Next.js dependencies...
call npm install
if errorlevel 1 (
    echo Failed to install Next.js dependencies
    exit /b 1
)

echo.
echo [2/3] Installing Python dependencies...
cd python-service
call pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install Python dependencies
    exit /b 1
)

echo.
echo [3/3] Installing Playwright browsers...
call playwright install chromium
if errorlevel 1 (
    echo Failed to install Playwright browsers
    exit /b 1
)

cd ..
echo.
echo Setup complete!
echo.
echo To start the application:
echo   1. Start Python service: cd python-service && python main.py
echo   2. Start Next.js app: npm run dev
echo.
pause
