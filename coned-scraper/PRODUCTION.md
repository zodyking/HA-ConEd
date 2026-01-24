# ConEd Scraper - Production Deployment Guide

## 🎯 Overview

This is a complete production-ready setup for automated ConEd billing data scraping with webhooks integration.

### Architecture

- **Backend**: Python FastAPI with Playwright (headless browser automation)
- **Frontend**: Next.js 15 React app with TypeScript
- **Database**: SQLite for logs and scrape history
- **Automation**: Background scheduler for automated scrapes
- **Integration**: Webhook support for Home Assistant and other services

## ✅ Production Readiness Checklist

### Backend (Python Service)
- ✅ Runs completely server-side in headless mode
- ✅ Background scheduler operates independently
- ✅ Webhooks sent only when data changes (database-based detection)
- ✅ Persistent storage for credentials, webhooks, and schedule
- ✅ SQLite database for scrape history
- ✅ Automatic error recovery and logging
- ✅ CORS enabled for frontend communication

### Frontend (Next.js App)
- ✅ Production build passes with 0 errors
- ✅ Optimized bundle size (~110 KB First Load JS)
- ✅ TypeScript type checking enabled
- ✅ React strict mode enabled
- ✅ Compression enabled
- ✅ Image optimization (AVIF/WebP)
- ✅ Standalone output for easy deployment

## 🚀 Quick Start - Production Mode

### 1. Start Python Backend

```bash
cd coned-scraper/python-service
start-production.bat
```

This will:
- Create/activate virtual environment
- Install dependencies
- Start FastAPI server on port 8000
- Enable headless browser mode
- Start background scheduler (if enabled)

### 2. Start Next.js Frontend

```bash
cd coned-scraper/app
start-production.bat
```

This will:
- Build the app if not already built
- Start production server on port 3000

### 3. Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📋 Initial Configuration

### Step 1: Set Credentials
1. Go to Settings tab
2. Enter your ConEd username, password, and TOTP secret
3. Click "Save Credentials"

### Step 2: Configure Webhooks (Optional)
1. Go to Settings tab
2. Enter webhook URLs for:
   - Latest Bill
   - Previous Bill
   - Account Balance
   - Last Payment
3. Click "Save Webhooks"
4. Click "Test Webhooks" to verify

### Step 3: Enable Automated Scraping
1. Go to Settings tab
2. Set scrape frequency (in seconds)
3. Toggle "Enable Automated Scraping"

## 🔄 How Automated Scraping Works

### Server-Side Operation
- **Completely independent of UI**: Scraping runs in Python backend
- **Headless browser**: No visible browser window
- **Background scheduler**: Runs as async task
- **Persistent across restarts**: Schedule saved to disk

### Change Detection
- Compares new scrape with previous scrape in database
- Only sends webhooks when data actually changes
- No separate state file needed
- Full history visible in Account Ledger page

### Webhook Triggers
Webhooks are sent ONLY when:
- Account balance changes
- New bill is posted
- Previous bill amount changes
- New payment is recorded

## 📊 Monitoring

### Logs
- Real-time logs visible in Dashboard
- Shows all scrape attempts, successes, errors
- Webhook send status
- Change detection results

### Account Ledger
- Complete history of all scrapes
- Shows extracted data for each scrape
- Useful for verifying change detection

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Scraper fails with browser errors
- **Solution**: Ensure Playwright browsers are installed
  ```bash
  python -m playwright install chromium
  ```

**Problem**: Automated scraping not running
- **Solution**: Check that schedule is enabled in Settings
- **Solution**: Check logs for error messages
- **Solution**: Verify credentials are saved

**Problem**: Webhooks not sending
- **Solution**: Verify webhook URLs are configured
- **Solution**: Check that data has actually changed
- **Solution**: Test webhooks manually with "Test Webhooks" button
- **Solution**: Check backend logs for webhook errors

### Frontend Issues

**Problem**: Build fails
- **Solution**: Run `npm install` to ensure dependencies are installed
- **Solution**: Check for TypeScript errors

**Problem**: Cannot connect to backend
- **Solution**: Ensure Python service is running on port 8000
- **Solution**: Check CORS configuration

## 🔐 Security Notes

### Credentials Storage
- Encrypted using Fernet (symmetric encryption)
- Encryption key stored in `data/.key`
- Credentials file: `data/credentials.json` (encrypted)
- **IMPORTANT**: Keep the `.key` file secure and backed up

### Webhook URLs
- Stored unencrypted in `data/webhooks.json`
- Consider using HTTPS URLs in production
- Use webhook secrets/tokens for additional security

### TOTP Secret
- Stored encrypted with credentials
- Generate new codes every 30 seconds
- Keep your TOTP secret secure

## 📁 Data Directory Structure

```
coned-scraper/python-service/data/
├── .key                          # Encryption key (DO NOT LOSE)
├── credentials.json              # Encrypted credentials
├── webhooks.json                 # Webhook configuration
├── schedule.json                 # Scraping schedule
├── scraper.db                    # SQLite database (logs & scrapes)
├── account_balance.png           # Last successful scrape screenshot
└── live_preview.png              # Real-time scrape preview
```

## 🔧 Advanced Configuration

### Change Scrape Frequency
Edit `schedule.json` or use the Settings UI:
```json
{
  "enabled": true,
  "frequency": 3600  // seconds (3600 = 1 hour)
}
```

### Environment Variables

**Python Service**:
- `PLAYWRIGHT_HEADLESS`: Set to `false` to see browser (debugging)
- `PYTHONUNBUFFERED`: Set to `1` for real-time logging

**Next.js**:
- Production mode automatically optimizes bundle size
- Standalone output includes only necessary files

## 📦 Deployment Options

### Windows (Current Setup)
- Use the provided `start-production.bat` scripts
- Run as Windows services for automatic startup

### Linux/macOS
- Create shell scripts similar to `.bat` files
- Use systemd (Linux) or launchd (macOS) for service management

### Docker
- Backend: FastAPI + Playwright
- Frontend: Next.js standalone build
- Use docker-compose for orchestration

## 🎓 Best Practices

1. **Regular Backups**: Backup the `data` directory regularly
2. **Monitor Logs**: Check logs daily for any issues
3. **Update Dependencies**: Keep Python and Node packages updated
4. **Webhook Testing**: Test webhooks after any configuration change
5. **Change Detection**: Review Account Ledger to verify data accuracy
6. **Frequency**: Set scrape frequency based on your needs (recommended: 4-24 hours)

## 📞 Support

For issues or questions:
1. Check logs in Dashboard
2. Review this documentation
3. Check Account Ledger for data issues
4. Test webhooks manually to isolate problems

## 🔄 Updates & Maintenance

### Update Python Dependencies
```bash
cd coned-scraper/python-service
pip install -r requirements.txt --upgrade
```

### Update Node Dependencies
```bash
cd coned-scraper/app
npm update
npm run build  # Test build
```

### Database Maintenance
- SQLite database auto-manages storage
- Clear old logs via Dashboard UI
- No manual maintenance required

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: ✅ Production Ready
