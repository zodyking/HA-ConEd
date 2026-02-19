# Con Edison

Home Assistant add-on repository for Con Edison account integration.

## What It Is

**Con Edison** is a Home Assistant add-on that connects to your Con Edison (utility) account. It syncs your bill history, payments, account balance, and exposes them as MQTT sensors so you can use the data in Home Assistant automations and dashboards.

Features:
- **Bill & payment history** — Ledger, PDF bills, payment tracking
- **Payee attribution** — For shared bills: assign payments to roommates/households, track who owes what
- **MQTT sensors** — Auto-discovered sensors for balance, latest bill, last payment, payee summaries
- **Automated scraping** — Configurable schedule or manual runs
- **IMAP integration** — Auto-match payments to payees from Con Edison confirmation emails

## Add-on

| Add-on | Description |
|--------|-------------|
| [Con Edison](coned_scraper/) | Con Edison account integration — bills, payments, balance, MQTT |

## Installation

1. Add this repository to your Home Assistant add-on store
2. Repository URL: `https://github.com/zodyking/HA-ConEd`
3. Install the **Con Edison** addon
4. Start the addon and open the panel from the sidebar

## Documentation

See [coned_scraper/DOCS.md](coned_scraper/DOCS.md) for addon configuration and usage.

## License

MIT License - See [LICENSE.md](LICENSE.md)
