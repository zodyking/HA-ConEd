# ConEd Scraper - Home Assistant Addon

Automated ConEd billing data scraper with MQTT and web UI. Access the panel directly from your Home Assistant sidebar.

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
3. (Optional) Configure MQTT for Home Assistant integration.
4. Enable the automated scraping schedule if desired.

## Data Persistence

All addon data (credentials, MQTT config, schedule, database) is stored in the addon configuration directory and persists across restarts.

## MQTT Integration with Home Assistant

Configure MQTT in the Settings tab. The addon publishes to MQTT topics for `account_balance`, `latest_bill`, `last_payment`, `previous_bill`, and payee summaries. Add MQTT sensors in Home Assistant to consume this data.

## Ingress

This addon uses Home Assistant Ingress. The web interface is accessed through the sidebar—no additional ports or network configuration required.

## Support

- [GitHub Repository](https://github.com/zodyking/conedison)
- [Home Assistant Community Forum](https://community.home-assistant.io)
