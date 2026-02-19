# ConEd Scraper

Automated ConEd billing data scraper with webhooks and web UI. Built with Next.js 15 and Python FastAPI.

## Deployment Options

| Option | Description |
|--------|-------------|
| **Home Assistant Addon** | Install from [HA-ConEd](https://github.com/zodyking/HA-ConEd) — ingress panel, single addon ([DOCS.md](DOCS.md)) |
| **Dokploy / Docker Compose** | Deploy `docker-compose.yml` to any Docker host |

## Quick Start

### Home Assistant Addon

1. Add repository: `https://github.com/zodyking/HA-ConEd`
2. Install **ConEd Scraper** addon
3. Start and open the panel from the sidebar

### Dokploy

1. Create project → Docker Compose
2. Connect `https://github.com/zodyking/conedison`, compose file: `coned_scraper/docker-compose.yml`
3. Deploy, attach domain to `web` service
4. Configure credentials and webhooks in Settings

### Local Development

```bash
# Python backend (port 8000)
cd python-service && run.bat   # or ./run.sh

# Next.js frontend (port 3000)
cd app && npm install && npm run dev
```

## Features

- Automated scraping with configurable schedule
- Smart webhooks (only on data changes)
- Encrypted credential storage
- Real-time logs and account ledger
- Webhook integration for Home Assistant

## Webhook Integration

Configure webhooks in Settings, then add to `configuration.yaml`:

```yaml
sensor:
  - platform: webhook
    webhook_id: YOUR_WEBHOOK_ID
    name: "ConEd Account Balance"
    state: "{{ trigger.json.data.account_balance }}"
    unit_of_measurement: "$"
```

Payloads: `account_balance`, `latest_bill`, `last_payment`, `previous_bill`

## Structure

```
├── config.yaml, build.yaml, Dockerfile   # HA addon
├── docker-compose.yml, Dockerfile.web    # Docker / Dokploy
├── rootfs/                               # S6 overlay (addon)
├── app/                                  # Next.js frontend
└── python-service/                      # Python FastAPI + Playwright
```

## Links

- [conedison](https://github.com/zodyking/conedison) — full project
- [HA-ConEd](https://github.com/zodyking/HA-ConEd) — addon repo
