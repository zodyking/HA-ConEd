# Con Edison

Con Edison account integration for Home Assistant. Syncs bills, payments, and balance; exposes MQTT sensors; supports payee tracking for shared accounts.

## Deployment Options

| Option | Description |
|--------|-------------|
| **Home Assistant Addon** | Install from [HA-ConEd](https://github.com/zodyking/HA-ConEd) — ingress panel, single addon ([DOCS.md](DOCS.md)) |
| **Dokploy / Docker Compose** | Deploy `docker-compose.yml` to any Docker host |

## Quick Start

### Home Assistant Addon

1. Add repository: `https://github.com/zodyking/HA-ConEd`
2. Install **Con Edison** addon
3. Start and open the panel from the sidebar

### Dokploy

1. Create project → Docker Compose
2. Connect `https://github.com/zodyking/conedison`, compose file: `coned_scraper/docker-compose.yml`
3. Deploy, attach domain to `web` service
4. Configure credentials and MQTT in Settings

### Local Development

```bash
# Python backend (port 8000)
cd python-service && run.bat   # or ./run.sh

# Vue frontend (port 3000)
cd frontend && npm install && npm run dev
```

## Features

- **Bill history & ledger** — View bills, payments, PDF bills
- **Payee tracking** — Assign payments to roommates/households; audit and reconcile shared bills
- **MQTT sensors** — Balance, latest bill, last payment, payee summaries; auto-discovery so no YAML config needed
- **Automated scraping** — Configurable schedule or manual runs
- **IMAP integration** — Match payments to payees from Con Edison confirmation emails
- **Encrypted credential storage**

## Structure

```
├── config.yaml, build.yaml, Dockerfile   # HA addon
├── docker-compose.yml, Dockerfile.web    # Docker / Dokploy
├── rootfs/                               # S6 overlay (addon)
├── frontend/                             # Vue 3 + Vite frontend
└── python-service/                       # Python FastAPI + Playwright
```

## Links

- [conedison](https://github.com/zodyking/conedison) — full project
- [HA-ConEd](https://github.com/zodyking/HA-ConEd) — addon repo
