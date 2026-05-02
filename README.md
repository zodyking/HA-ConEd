# HA-ConEd — Con Edison for Home Assistant

Home Assistant add-on that connects your **Con Edison** account to Home Assistant: ledger, bills, balance, shared payees, MQTT entities, optional meter usage (Opower), and PDF hosting.

The add-on release version is the `version` key in [`coned_scraper/config.yaml`](coned_scraper/config.yaml).

## Features

| Area | What you get |
|------|----------------|
| **Ledger** | Bills, payments, balance, due dates; consistent ordering with the web UI |
| **Bill PDFs** | Store and host PDFs; optional auto-download; MQTT exposes a link in attributes |
| **Payees** | Split responsibility, cards, payments — Bill-only or rollover breakdown |
| **Meter** | Forecast, usage-to-date, projected usage/bill via Opower (typical **1–24 h delay**); **Daily Usage** chart uses **15‑minute** intervals with calendar days in **US Eastern** |
| **MQTT** | Auto-discovered sensors for balance, bills, usage, PDF URL, payee summary, dates |
| **TTS / IMAP** | Optional alerts and payment detection from email |

## MQTT sensors (discovery)

| Sensor | Description |
|--------|-------------|
| `ConEd_account_balance` | Account balance (USD) |
| `ConEd_latest_bill` | Latest bill amount |
| `ConEd_previous_bill` | Previous bill amount |
| `ConEd_last_payment` | Last payment amount |
| `ConEd_bill_pdf_url` | State shows "Check attributes"; PDF URL is in attributes |
| `ConEd_payee_summary` | Payee breakdown (balance, shares) |
| `ConEd_due_date` | Bill due date |
| `ConEd_kwh_cost` | $/kWh from bill |
| `ConEd_last_bill_kwh` | kWh from last bill |
| `ConEd_current_usage_cost` | Cost to date (USD) |
| `ConEd_billing_start_date` | Billing period start |
| `ConEd_billing_end_date` | Billing period end |
| `ConEd_current_cycle_usage` | Usage to date (kWh) |
| `ConEd_forecasted_usage` | Projected usage (kWh) |

## Installation

1. In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/zodyking/HA-ConEd`
3. Install **Con Edison**, configure options, start the add-on
4. Open the panel from the sidebar (ingress)

## Documentation

Full configuration and usage: [`coned_scraper/DOCS.md`](coned_scraper/DOCS.md).

## Repository layout

| Path | Role |
|------|------|
| [`coned_scraper/`](coned_scraper/) | Add-on manifest, Docker/run layout, Python API, Vue frontend |
| [`repository.yaml`](repository.yaml) | HA add-on store metadata |

Do **not** commit credentials, `.env` files, or API dumps; keep secrets in the add-on UI or HA secrets.

## License

MIT — see [`LICENSE.md`](LICENSE.md).
