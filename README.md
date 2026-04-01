# Con Edison

Home Assistant add-on for Con Edison account integration — bills, payments, balance, MQTT sensors, and more.

## Features

- **Account ledger** — Bill history, payments, account balance, due dates
- **Bill PDFs** — Store, host, and view PDFs; auto-download during scrape; send PDF URL to MQTT
- **Payee tracking** — Shared bills: add users, assign responsibility %, link cards, attribute payments; Bill only / Rollover breakdown
- **Meter tracking** — Usage, forecast, projected bill (Opower API; hourly data, 1–24h delay)
- **TTS alerts** — Text-to-speech via HA API or MQTT; wait for media player idle
- **IMAP** — Auto-detect payments from Con Edison confirmation emails
- **Automated scrape** — Configurable schedule or manual run

## MQTT Sensors (auto-discovered)

| Sensor | Description |
|--------|-------------|
| `ConEd_account_balance` | Account balance (USD) |
| `ConEd_latest_bill` | Latest bill amount |
| `ConEd_previous_bill` | Previous bill amount |
| `ConEd_last_payment` | Last payment amount |
| `ConEd_bill_pdf_url` | State shows "Check attributes"; open attributes for the PDF URL |
| `ConEd_payee_summary` | Payee breakdown (balance, shares) |
| `ConEd_due_date` | Bill due date |
| `ConEd_kwh_cost` | $/kWh from bill |
| `ConEd_last_bill_kwh` | kWh from last bill |
| `ConEd_current_usage_cost` | Cost to date (USD) |
| `ConEd_billing_start_date` | Billing period start |
| `ConEd_billing_end_date` | Billing period end |
| `ConEd_current_cycle_usage` | Usage to date (kWh) |
| `ConEd_forecasted_usage` | Projected usage (kWh) |

## Add-on

| Add-on | Description |
|--------|-------------|
| [Con Edison](coned_scraper/) | Con Edison integration — ledger, PDFs, payees, meter, MQTT |

## Installation

1. Add repository: `https://github.com/zodyking/HA-ConEd`
2. Install **Con Edison** addon
3. Start addon and open panel from sidebar

## Documentation

[coned_scraper/DOCS.md](coned_scraper/DOCS.md) — configuration and usage.

## License

MIT — See [LICENSE.md](LICENSE.md)
