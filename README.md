# ConEd Scraper

A Next.js application with Python backend service for automating ConEd account login with TOTP authentication.

## Features

- **Next.js Frontend**: Modern React UI with settings page
- **Python FastAPI Service**: Backend API for TOTP generation and browser automation
- **TOTP Support**: Generates TOTP codes matching Google Authenticator
- **Headless Browser Automation**: Uses Playwright to automate login with character-by-character typing (never pastes)
- **Secure Storage**: Encrypted credential storage
- **Live TOTP Display**: Real-time TOTP code display with countdown timer

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Playwright browsers (installed automatically)

## Setup

### 1. Install Next.js Dependencies

```bash
npm install
```

### 2. Setup Python Service

```bash
cd python-service
pip install -r requirements.txt
playwright install chromium
```

### 3. Start the Python Service

```bash
cd python-service
python main.py
```

The API will run on `http://localhost:8000`

### 4. Start Next.js Development Server

In a new terminal:

```bash
npm run dev
```

The app will run on `http://localhost:3000`

## Usage

1. Open `http://localhost:3000` in your browser
2. Enter your ConEd username/email, password, and TOTP secret
3. Click "Save Settings"
4. The current TOTP code will be displayed and update automatically
5. Click "Test Login" to trigger the automated login process

## TOTP Secret Format

The TOTP secret should be a base32-encoded string (same format as Google Authenticator). Example: `JBSWY3DPEHPK3PXP`

## Security Notes

- Credentials are encrypted at rest using Fernet encryption
- Encryption key is stored in `python-service/data/.key`
- Never commit credentials or encryption keys to version control
- The Python service should only be accessible locally or behind proper authentication

## Project Structure

```
.
├── app/                    # Next.js App Router
│   ├── components/         # React components
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   └── globals.css         # Global styles
├── python-service/         # Python FastAPI service
│   ├── main.py            # FastAPI app and endpoints
│   ├── browser_automation.py  # Playwright automation
│   ├── requirements.txt   # Python dependencies
│   └── data/              # Encrypted credentials storage
├── package.json           # Node.js dependencies
└── README.md             # This file
```

## API Endpoints

- `GET /api/totp` - Get current TOTP code
- `GET /api/settings` - Get saved credentials (masked)
- `POST /api/settings` - Save credentials
- `POST /api/login` - Trigger login automation

## Troubleshooting

- **TOTP not generating**: Ensure the TOTP secret is valid base32 format
- **Login fails**: Check the screenshots saved in `python-service/` directory
- **API connection error**: Ensure Python service is running on port 8000
- **Browser automation fails**: Ensure Playwright browsers are installed (`playwright install chromium`)
