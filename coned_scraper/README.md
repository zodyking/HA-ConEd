# Con Edison

Con Edison account integration for Home Assistant. Syncs bills, payments, and balance; exposes MQTT sensors; supports payee tracking for shared accounts.

## Installation

1. Add repository: `https://github.com/zodyking/HA-ConEd`
2. Install **Con Edison** addon
3. Start and open the panel from the sidebar

## Features

- **Bill history & ledger** — View bills, payments, PDF bills
- **Payee tracking** — Assign payments to roommates/households; audit and reconcile shared bills
- **MQTT sensors** — Balance, latest bill, last payment, payee summaries; auto-discovery so no YAML config needed
- **Automated scraping** — Configurable schedule or manual runs
- **IMAP integration** — Match payments to payees from Con Edison confirmation emails
- **Encrypted credential storage**

## Documentation

See [DOCS.md](DOCS.md) for addon configuration and usage.

## Structure

```
├── config.yaml, build.yaml, Dockerfile   # HA addon
├── rootfs/                               # S6 overlay
├── frontend/                             # Vue 3 + Vite frontend
└── python-service/                       # Python FastAPI + Playwright
```
