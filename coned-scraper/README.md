# ConEd Scraper - Production Ready

Automated ConEd billing data scraper with webhooks and web UI. Built with Next.js 15 and Python FastAPI.

## 🚀 Quick Deploy to Dokploy

This project is configured for one-click deployment to Dokploy using Docker Compose.

### Prerequisites
- Dokploy instance running
- GitHub repository: `https://github.com/zodyking/conedison` (or your fork)

### Deployment Steps

1. **In Dokploy UI**:
   - Create new project → Choose "Docker Compose"
   - Connect GitHub: `https://github.com/zodyking/conedison`
   - Set compose file: `docker-compose.yml`
   - Click Deploy

2. **Configure Domain**:
   - Go to Domains tab
   - Attach your domain to the `web` service
   - Dokploy will auto-configure Traefik routing

3. **First-Time Setup** (after deployment):
   - Visit your domain
   - Go to Settings tab
   - Enter ConEd credentials (encrypted automatically)
   - Configure webhooks (optional)
   - Enable automated scraping schedule

### Architecture

```
┌─────────────────┐
│   Traefik       │ ← Dokploy's reverse proxy
│  (dokploy)      │
└────────┬────────┘
         │
         ├─→ web:3000     (Next.js UI)
         │    └─→ /api/* proxies to ↓
         │
         └─→ api:8000     (Python FastAPI + Playwright)
                 └─→ data/ (volume for persistence)
```

## 🏗️ Local Development

### Python Backend

```bash
cd coned-scraper/python-service

# Windows
run.bat

# Linux/Mac
./run.sh
```

Runs on: http://localhost:8000

### Next.js Frontend

```bash
cd coned-scraper/app
npm install
npm run dev
```

Runs on: http://localhost:3000

## 📦 What's Included

### Services

- **web** (Next.js 15): Modern React UI with TypeScript
- **api** (Python FastAPI): Headless browser automation + scheduling

### Features

- ✅ **Automated Scraping**: Schedule scrapes at configurable intervals
- ✅ **Smart Webhooks**: Only sends when data changes (database-based detection)
- ✅ **Encrypted Storage**: Credentials encrypted at rest
- ✅ **Headless Browser**: Playwright for reliable scraping
- ✅ **Real-time Logs**: Monitor scrape activity
- ✅ **Account Ledger**: Full bill/payment history

### Data Persistence

The `api-data` volume stores:
- Encrypted credentials
- Webhook configurations
- Scraping schedule
- SQLite database (logs & history)
- Screenshots

## 🔧 Configuration

### Environment Variables (optional in Dokploy)

**Web Service:**
- `API_BASE_URL`: Backend URL (defaults to `http://api:8000` in Docker)
- `NODE_ENV`: Set to `production`

**API Service:**
- `PLAYWRIGHT_HEADLESS`: Always `true` in Docker
- `PYTHONUNBUFFERED`: Set to `1`

### Application Settings (configured via UI)

1. **Credentials** (Settings → Credentials):
   - ConEd username
   - ConEd password  
   - TOTP secret (from Google Authenticator setup)

2. **Webhooks** (Settings → Webhooks):
   - Latest Bill URL
   - Previous Bill URL
   - Account Balance URL
   - Last Payment URL

3. **Schedule** (Settings → Schedule):
   - Enable/disable automated scraping
   - Frequency in seconds (recommended: 14400 = 4 hours)

## 📊 Webhook Integration

### Home Assistant Example

Configure webhooks in Settings, then add to Home Assistant `configuration.yaml`:

```yaml
sensor:
  - platform: webhook
    webhook_id: YOUR_WEBHOOK_ID
    name: "ConEd Account Balance"
    state: "{{ trigger.json.data.account_balance }}"
    unit_of_measurement: "$"
```

### Webhook Payloads

**Account Balance:**
```json
{
  "event_type": "account_balance",
  "timestamp": "2026-01-23T12:00:00",
  "data": {
    "account_balance": 123.45,
    "account_balance_raw": "$123.45"
  }
}
```

**Latest Bill:**
```json
{
  "event_type": "latest_bill",
  "timestamp": "2026-01-23T12:00:00",
  "data": {
    "bill_total": "$150.00",
    "bill_cycle_date": "1/21/2026",
    "month_range": "Dec 21 - Jan 21",
    "bill_date": "2026-01-21"
  }
}
```

**Last Payment:**
```json
{
  "event_type": "last_payment",
  "timestamp": "2026-01-23T12:00:00",
  "data": {
    "amount": "$150.00",
    "payment_date": "1/23/2026",
    "bill_cycle_date": "1/21/2026",
    "description": "Payment Received"
  }
}
```

## 🐳 Docker Architecture

### Web Service (Next.js)
- Multi-stage build for optimal size
- Standalone output mode
- API calls proxied via rewrites
- Production-optimized bundle

### API Service (Python)
- Chromium browser included
- All dependencies installed
- Persistent data volume
- Headless mode enforced

## 📝 API Documentation

Once deployed, visit:
- **Swagger UI**: `https://your-domain/docs`
- **ReDoc**: `https://your-domain/redoc`

Key endpoints:
- `POST /api/scraper/start` - Manual scrape
- `GET /api/logs` - Recent logs
- `GET /api/scraped-data` - Scrape history
- `POST /api/credentials` - Save credentials
- `POST /api/webhooks` - Configure webhooks
- `POST /api/schedule` - Set scraping schedule

## 🔒 Security

- ✅ Credentials encrypted with Fernet (symmetric encryption)
- ✅ Encryption key stored securely in data volume
- ✅ No secrets in environment variables
- ✅ HTTPS enforced via Traefik (Dokploy default)
- ✅ CORS configured for same-origin only

## 📈 Monitoring

### Via UI
- **Dashboard**: Real-time logs and status
- **Account Ledger**: Complete scrape history

### Via Dokploy
- Container logs (stdout/stderr)
- Resource usage metrics
- Health checks

## 🛠️ Troubleshooting

### Scraping Fails
1. Check credentials in Settings
2. Verify TOTP secret is correct
3. Review logs in Dashboard
4. Ensure ConEd website is accessible

### Webhooks Not Sending
1. Verify webhook URLs are configured
2. Check that data has actually changed
3. Use "Test Webhooks" button
4. Review API service logs

### Container Issues
1. Check Dokploy logs for build errors
2. Verify volumes are mounted correctly
3. Ensure Playwright browsers installed (automatic in Dockerfile)

## 📦 Repository Structure

```
coned-scraper/
├── docker-compose.yml           # Dokploy deployment
├── Dockerfile.web               # Next.js container
├── .dockerignore                # Build optimization
├── PRODUCTION.md                # Detailed production guide
├── PRODUCTION-CHECKLIST.md      # Deployment checklist
│
├── app/                         # Next.js frontend
│   ├── app/                    # App Router
│   │   ├── page.tsx           # Main page
│   │   ├── layout.tsx         # Root layout
│   │   └── not-found.tsx      # 404 page
│   ├── components/             # React components
│   │   ├── Dashboard.tsx      # Main dashboard
│   │   ├── Settings.tsx       # Configuration
│   │   └── AccountLedger.tsx  # History view
│   ├── next.config.ts          # Next.js config + API rewrites
│   ├── package.json
│   └── start-production.bat
│
└── python-service/              # Python backend
    ├── Dockerfile              # Python container
    ├── main.py                 # FastAPI server
    ├── browser_automation.py   # Playwright scraper
    ├── database.py             # SQLite operations
    ├── webhook_client.py       # Webhook sender
    ├── requirements.txt
    └── start-production.bat
```

## 🔄 Updates & Maintenance

### Updating the App
1. Push changes to GitHub
2. In Dokploy, click "Redeploy"
3. Dokploy pulls latest code and rebuilds

### Backup Data
Export the `api-data` volume regularly:
```bash
docker run --rm -v conedison_api-data:/data -v $(pwd):/backup alpine tar czf /backup/api-data-backup.tar.gz /data
```

## 📚 Additional Documentation

- **Full Production Guide**: See `PRODUCTION.md`
- **Deployment Checklist**: See `PRODUCTION-CHECKLIST.md`
- **Python Service**: See `python-service/README.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with Docker Compose
5. Submit a pull request

## 📄 License

MIT License - Feel free to use and modify

## 🔗 Links

- **GitHub**: https://github.com/zodyking/conedison
- **Dokploy Docs**: https://docs.dokploy.com

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: January 2026
