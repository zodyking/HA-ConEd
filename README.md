# HA-ConEd — Con Edison for Home Assistant

Home Assistant add-on that connects your **Con Edison** account to Home Assistant: ledger, bills, balance, shared payees, MQTT entities, optional meter usage (Opower), and PDF hosting.

The add-on release version is the `version` key in [`coned_scraper/config.yaml`](coned_scraper/config.yaml).

**There is no `manifest.json` for the add-on.** Home Assistant Supervisor reads only `coned_scraper/config.yaml` for update detection. The file [`coned_scraper/integration/coned_connect/manifest.json`](coned_scraper/integration/coned_connect/manifest.json) is for the optional HACS custom integration and does not control add-on updates.

### If updates are not detected

1. In **Settings → Add-ons → Add-on Store**, open the **⋮** menu and choose **Reload** (not only “Check for updates”).
2. Confirm the repository URL is exactly `https://github.com/zodyking/HA-ConEd` with **no `#tag` or branch suffix** (for example, not `#1.3.89`).
3. If it still shows the old version, remove the repository and add it again, then **Reload**.
4. The update dialog may show the full `CHANGELOG.md` even when the store is stale — that does not mean the new version was detected. Check **Latest version** in the dialog; it must be higher than **Installed version** before **Update** is enabled.

To bump the add-on version when releasing:

```bash
python3 scripts/sync_addon_version.py 1.3.94
```

This updates `config.yaml`, `main.py` `CODE_VERSION`, and the startup log in `rootfs`.

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
