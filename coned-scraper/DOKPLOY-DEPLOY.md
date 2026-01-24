# 🚀 Dokploy Deployment Guide

## Quick Deploy (5 minutes)

Your ConEd Scraper is ready for Dokploy! Just follow these steps.

### Step 1: Create Project in Dokploy

1. Log into your Dokploy dashboard
2. Click **"Create Project"**
3. Choose **"Docker Compose"**
4. Name it: `coned-scraper` or any name you prefer

### Step 2: Connect GitHub Repository

**Choose ONE repository:**

- **Option A** (Recommended): `https://github.com/zodyking/conedison`
- **Option B**: `https://github.com/zodyking/coned-scraper`

Both repositories are identical and ready for deployment.

### Step 3: Configure Deployment

In the Dokploy project settings:

**Build Configuration:**
- **Compose File Path**: `coned-scraper/docker-compose.yml`
- **Branch**: `main`
- Leave other settings as default

Click **"Deploy"** and wait for build to complete (~5-10 minutes first time).

### Step 4: Configure Domain

After deployment succeeds:

1. Go to **"Domains"** tab
2. Click **"Add Domain"**
3. Select service: **`web`**
4. Enter your domain: `coned.yourdomain.com`
5. Click **"Save"**

Dokploy will automatically configure Traefik routing and SSL certificate (if DNS is configured).

### Step 5: First-Time Setup

Visit your domain and complete setup:

1. **Configure Credentials** (Settings tab):
   ```
   - ConEd Username: your_username
   - ConEd Password: your_password
   - TOTP Secret: YOUR_TOTP_SECRET_FROM_GOOGLE_AUTHENTICATOR
   ```
   Click "Save Credentials" (automatically encrypted)

2. **Configure Webhooks** (Settings tab - Optional):
   ```
   - Latest Bill: https://homeassistant.local/api/webhook/latest_bill
   - Previous Bill: https://homeassistant.local/api/webhook/prev_bill
   - Account Balance: https://homeassistant.local/api/webhook/balance
   - Last Payment: https://homeassistant.local/api/webhook/payment
   ```
   Click "Save Webhooks", then "Test Webhooks"

3. **Enable Schedule** (Settings tab):
   ```
   - Frequency: 14400 (4 hours in seconds)
   - Toggle: "Enable Automated Scraping" ON
   ```

Done! Your scraper will now run automatically every 4 hours.

---

## Architecture Overview

```
Internet → Traefik (Dokploy) → web:3000 (Next.js UI)
                                    ↓
                               api:8000 (Python + Playwright)
                                    ↓
                             volume: api-data (persistent)
```

### What Gets Deployed

**Services:**
- `web`: Next.js 15 frontend (port 3000)
- `api`: Python FastAPI + Playwright (port 8000)

**Network:**
- Both services on `dokploy-network`
- Internal communication: `web` → `api:8000`
- External access: Only `web` exposed via Traefik

**Persistent Storage:**
- `api-data` volume: credentials, config, database, screenshots

---

## Verification Checklist

After deployment, verify these work:

### ✅ Web Service
- [ ] Can access your domain
- [ ] Settings page loads
- [ ] Dashboard page loads
- [ ] Account Ledger page loads

### ✅ API Service
- [ ] Visit `https://your-domain/docs` (Swagger UI)
- [ ] API returns data (check Dashboard logs)
- [ ] Manual scrape works (click "Run Scrape Now")

### ✅ Automation
- [ ] Credentials saved successfully
- [ ] Manual scrape completes without errors
- [ ] Schedule enabled (check Dashboard for next run time)
- [ ] Webhooks tested (if configured)

---

## Troubleshooting

### Build Fails

**Error: Playwright dependencies not found**
- This is handled automatically in the Dockerfile
- If still failing, check Dokploy build logs

**Error: Out of memory**
- Increase memory limit in Dokploy project settings
- Minimum recommended: 2GB RAM

### Deployment Succeeds but Site Unreachable

**Check Domain Configuration:**
1. Verify DNS points to your Dokploy server IP
2. Check domain is attached to `web` service (not `api`)
3. Wait 1-2 minutes for Traefik to update routes

**Check Logs:**
```
Dokploy → Your Project → Logs tab
- Select service: web
- Look for startup errors
```

### Scraping Fails

**Error: Invalid credentials**
- Double-check username/password in Settings
- Verify TOTP secret is correct (try generating a code manually)

**Error: Timeout**
- ConEd website may be slow or down
- Try increasing timeout in `browser_automation.py` (line ~95)
- Restart deployment after changes

**Error: Browser not found**
- Dockerfile automatically installs Chromium
- If failing, check API service logs
- Verify Playwright installation succeeded during build

### Webhooks Not Sending

1. **Check webhook URLs** in Settings
2. **Verify data changed** (webhooks only sent on changes)
3. **Test manually** with "Test Webhooks" button
4. **Check API logs** for webhook send status:
   ```
   Dokploy → Your Project → Logs → Select: api
   ```

### Data Not Persisting

**Volume Issue:**
- Dokploy creates volume automatically
- Check volume exists:
  ```
  Dokploy → Your Project → Volumes tab
  ```
- If missing, recreate project (volume will auto-create)

---

## Updating Your Deployment

### Push Changes to GitHub

```bash
# Make your changes locally
git add -A
git commit -m "Your changes"
git push origin main
```

### Redeploy in Dokploy

1. Go to your project in Dokploy
2. Click **"Redeploy"**
3. Dokploy pulls latest code and rebuilds
4. Wait for deployment to complete

**Note:** Your data (credentials, config, database) persists across redeployments.

---

## Monitoring

### Via Dokploy Dashboard

1. **Logs**: Real-time container logs
   - Select service: `web` or `api`
   - Filter by time range

2. **Metrics**: Resource usage
   - CPU usage
   - Memory usage
   - Network traffic

3. **Health**: Service status
   - Running / Stopped
   - Restart count
   - Uptime

### Via Application UI

1. **Dashboard**: Latest scrape logs
2. **Account Ledger**: Complete history
3. **Settings**: Current configuration

---

## Backup & Restore

### Backup Data Volume

In Dokploy terminal or SSH:

```bash
# Create backup
docker run --rm \
  -v conedison_api-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/api-data-backup.tar.gz /data

# Download backup file from server
```

### Restore Data Volume

```bash
# Stop services first in Dokploy UI

# Restore backup
docker run --rm \
  -v conedison_api-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/api-data-backup.tar.gz --strip-components=1"

# Restart services in Dokploy UI
```

---

## Advanced Configuration

### Environment Variables (Optional)

Add in Dokploy project settings → Environment tab:

**For web service:**
```env
NODE_ENV=production
API_BASE_URL=http://api:8000
```

**For api service:**
```env
PLAYWRIGHT_HEADLESS=true
PYTHONUNBUFFERED=1
```

These are already set in `docker-compose.yml`, only override if needed.

### Custom Domain Setup

If using your own domain:

1. **DNS Configuration**:
   ```
   Type: A Record
   Name: coned (or @)
   Value: YOUR_DOKPLOY_SERVER_IP
   TTL: 300
   ```

2. **Add in Dokploy**:
   - Domains tab → Add Domain
   - Enter: `coned.yourdomain.com`
   - Service: `web`
   - SSL: Auto (Let's Encrypt)

3. **Wait for DNS propagation** (5-30 minutes)

---

## Performance Tips

### Optimize Scraping Frequency

Recommended schedules based on usage:

- **Heavy use**: 7200 seconds (2 hours)
- **Normal use**: 14400 seconds (4 hours) ← Default
- **Light use**: 43200 seconds (12 hours)
- **Minimal**: 86400 seconds (24 hours)

Less frequent = lower server load and faster response times.

### Resource Requirements

**Minimum:**
- 2 CPU cores
- 2GB RAM
- 10GB disk

**Recommended:**
- 4 CPU cores
- 4GB RAM
- 20GB disk

---

## Support

### Documentation
- **Full Production Guide**: `/PRODUCTION.md`
- **Deployment Checklist**: `/PRODUCTION-CHECKLIST.md`
- **Python Service Docs**: `/python-service/README.md`

### Dokploy Resources
- [Dokploy Documentation](https://docs.dokploy.com)
- [Docker Compose Docs](https://docs.dokploy.com/docs/core/docker-compose)
- [Domain Configuration](https://docs.dokploy.com/docs/core/domains)

### GitHub
- Repository: https://github.com/zodyking/conedison
- Issues: https://github.com/zodyking/conedison/issues

---

**Happy Deploying! 🚀**

*Last Updated: January 2026*
