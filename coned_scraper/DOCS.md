# Con Edison - Home Assistant Addon

Con Edison account integration for Home Assistant. Syncs bills, payments, and balance; exposes MQTT sensors; supports payee tracking for shared accounts. Access the panel directly from your Home Assistant sidebar.

## Installation

1. Add this repository to your Home Assistant add-on store (if using a custom repository).
2. Install the "Con Edison" addon.
3. Start the addon.
4. Open the Con Edison panel from the Home Assistant sidebar.

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

1. Open the Con Edison panel from the sidebar.
2. Go to **Settings** and enter your Con Edison credentials:
   - ConEd username
   - ConEd password
   - TOTP secret (from Google Authenticator)
3. (Optional) Configure MQTT for Home Assistant integration.
4. Enable the automated scraping schedule if desired.

## Data Persistence

All addon data (credentials, MQTT config, schedule, database) is stored in the addon configuration directory and persists across restarts.

## TTS Alerts

Configure TTS (text-to-speech) in **Settings → TTS Alerts**. Messages use format `(prefix), (message)` like [Home-Energy](https://github.com/zodyking/Home-Energy).

**Direct HA API:** When running as a Home Assistant addon, TTS is sent directly via the HA REST API — no automations needed. The addon uses `homeassistant_api` to call `tts.*` and `media_player.*` services.

**Media player idle:** When "Wait for media player idle" is enabled, the addon checks the media player state and waits (up to 5 minutes) until it is `idle` before playing, so TTS doesn’t interrupt music or other playback.

**MQTT fallback:** When running outside the addon (e.g. dev), TTS requests are published to `coned/tts/request` and require an HA automation to handle them.

## MQTT Integration with Home Assistant

Configure MQTT in the Settings tab. The addon publishes to MQTT topics for `account_balance`, `latest_bill`, `last_payment`, `previous_bill`, `tts/request`, and payee summaries.

**MQTT Discovery (enabled by default):** When enabled, the addon publishes Home Assistant MQTT discovery configs so sensors are **auto-registered**—no manual `configuration.yaml` needed. After configuring MQTT and running a scrape, sensors such as `sensor.coned_latest_bill`, `sensor.coned_account_balance`, `sensor.coned_last_payment`, etc. appear automatically under Settings → Devices & services → MQTT. You can disable discovery in MQTT Settings if you prefer manual YAML configuration.

## Ingress

This addon uses Home Assistant Ingress. The web interface is accessed through the sidebar—no additional ports or network configuration required.

## Support

- [GitHub Repository](https://github.com/zodyking/HA-ConEd)
- [Home Assistant Community Forum](https://community.home-assistant.io)
