@echo off
REM Production startup script for ConEd Scraper Next.js UI

echo ========================================
echo ConEd Scraper - Production UI
echo ========================================
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18 or higher
    pause
    exit /b 1
)

REM Check if .next build folder exists
if not exist ".next" (
    echo.
    echo No production build found. Building now...
    echo This may take a minute...
    call npm run build
    if %errorlevel% neq 0 (
        echo ERROR: Build failed
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Starting Production Server
echo ========================================
echo UI will be available at: http://localhost:3000
echo.
echo IMPORTANT: Make sure the Python backend is running at:
echo           http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the Next.js production server
npm run start

REM If the server stops, pause to see any error messages
pause
