# ConEd Scraper - Home Assistant Addon

Automated ConEd billing data scraper with webhooks and web UI. Access the panel directly from your Home Assistant sidebar.

## Installation

1. Add this repository to your Home Assistant add-on store (if using a custom repository).
2. Install the "ConEd Scraper" addon.
3. Start the addon.
4. Open the ConEd Scraper panel from the Home Assistant sidebar.

## Configuration

### Option: `log_level`

Controls the verbosity of addon logs. Default: `info`

- `trace` - Most verbose
- `debug` - Detailed debug information
- `info` - Normal operation (recommended)
- `warning` - Warnings only
- `error` - Errors only
- `fatal` - Critical failures only

## First-Time Setup

1. Open the ConEd Scraper panel from the sidebar.
2. Go to **Settings** and enter your ConEd credentials:
   - ConEd username
   - ConEd password
   - TOTP secret (from Google Authenticator)
3. (Optional) Configure webhooks for Home Assistant integration.
4. Enable the automated scraping schedule if desired.

## Data Persistence

All addon data (credentials, webhooks, schedule, database) is stored in the addon configuration directory and persists across restarts.

## Webhook Integration with Home Assistant

Configure webhooks in the Settings tab, then add sensors to your `configuration.yaml`:

```yaml
sensor:
  - platform: webhook
    webhook_id: YOUR_WEBHOOK_ID
    name: "ConEd Account Balance"
    state: "{{ trigger.json.data.account_balance }}"
    unit_of_measurement: "$"
```

Webhook payloads include: `account_balance`, `latest_bill`, `last_payment`, `previous_bill`.

## Ingress

This addon uses Home Assistant Ingress. The web interface is accessed through the sidebar—no additional ports or network configuration required.

## Support

- [GitHub Repository](https://github.com/zodyking/conedison)
- [Home Assistant Community Forum](https://community.home-assistant.io)
