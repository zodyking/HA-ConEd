# Setup Complete! ✅

## Installation Summary

### ✅ Next.js Dependencies
- Installed successfully (604 packages)
- Note: 4 vulnerabilities detected (run `npm audit fix` if needed)

### ✅ Python Dependencies
- FastAPI: ✅ Installed
- Uvicorn: ✅ Installed  
- PyOTP: ✅ Installed
- Playwright: ✅ Installed (v1.57.0)
- Cryptography: ✅ Installed
- Pydantic: ✅ Installed
- All other dependencies: ✅ Installed

### ✅ Playwright Browsers
- Chromium: ✅ Installed
- Chromium Headless Shell: ✅ Installed
- FFMPEG: ✅ Installed
- Winldd: ✅ Installed

## Next Steps

### 1. Start the Python Service
Open a terminal and run:
```bash
cd python-service
python main.py
```
The API will be available at: `http://localhost:8000`

### 2. Start the Next.js App
Open another terminal and run:
```bash
npm run dev
```
The app will be available at: `http://localhost:3000`

### 3. Configure Your Credentials
1. Open `http://localhost:3000` in your browser
2. Enter your ConEd username, password, and TOTP secret
3. Click "Save Settings"
4. View the live TOTP code display
5. Click "Test Login" to trigger automation

## Quick Commands

**Start Python Service:**
```bash
cd python-service
python main.py
```

**Start Next.js (in separate terminal):**
```bash
npm run dev
```

**Or use the batch files:**
- `python-service\start.bat` - Start Python service
- `setup.bat` - Re-run setup (if needed)

## Troubleshooting

- **Python service won't start**: Make sure port 8000 is not in use
- **Next.js won't start**: Make sure port 3000 is not in use  
- **TOTP not generating**: Verify your TOTP secret is valid base32 format
- **Login fails**: Check screenshots in `python-service/` directory for debugging

## Project Structure

```
ConEd Scrapper/
├── app/                    # Next.js App Router
│   ├── components/
│   │   └── Settings.tsx   # Settings UI component
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── python-service/         # Python FastAPI service
│   ├── main.py           # API endpoints
│   ├── browser_automation.py  # Playwright automation
│   ├── requirements.txt
│   └── data/             # Encrypted credentials (created on first save)
└── package.json
```

## API Endpoints

- `GET http://localhost:8000/api/totp` - Get current TOTP code
- `GET http://localhost:8000/api/settings` - Get saved credentials
- `POST http://localhost:8000/api/settings` - Save credentials
- `POST http://localhost:8000/api/login` - Trigger login automation

## Security Notes

- Credentials are encrypted using Fernet encryption
- Encryption key stored in `python-service/data/.key`
- Never commit credentials or `.key` file to version control
- The `.gitignore` file is configured to exclude sensitive data

Setup is complete! You're ready to use the ConEd scraper. 🚀
