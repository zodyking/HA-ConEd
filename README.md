# ConEd Scraper - Home Assistant Addon Repository

This repository contains the ConEd Scraper addon for Home Assistant.

## Quick Start

1. **Add this repository to Home Assistant:**
   - Go to **Supervisor** → **Add-on Store**
   - Click the three dots (⋮) → **Repositories**
   - Add: `https://github.com/zodyking/coned-scraper`
   - Click **Add**

2. **Install the addon:**
   - Find "ConEd Scraper" in the addon store
   - Click **Install**
   - Configure your ConEd credentials
   - Start the addon

3. **Configure Home Assistant sensors:**
   - See `coned-scraper/home-assistant-config.yaml` for sensor configuration
   - Add the sensors to your `configuration.yaml`

## Repository Structure

```
.
├── repository.json          # Repository metadata
└── coned-scraper/          # Addon directory
    ├── config.json         # Addon configuration
    ├── Dockerfile          # Docker image definition
    ├── run.sh              # Startup script
    ├── README.md           # Addon documentation
    ├── home-assistant-config.yaml  # HA sensor config example
    └── python-service/     # Python application code
        ├── main.py
        ├── browser_automation.py
        ├── database.py
        ├── mqtt_client.py
        ├── change_detection.py
        ├── sensor_publisher.py
        └── requirements.txt
```

## Features

- **Automated Scraping**: Scheduled scraping of ConEd account data
- **TOTP Support**: Generates TOTP codes matching Google Authenticator
- **Headless Browser Automation**: Uses Playwright to automate login
- **Secure Storage**: Encrypted credential storage
- **MQTT Integration**: Publishes sensors to Home Assistant
- **Change Detection**: Only updates sensors when values change

## Sensors

The addon publishes 4 MQTT sensors:
- Account Balance
- Most Recent Bill Amount
- Previous Bill Amount
- Last Payment Amount

See `coned-scraper/home-assistant-config.yaml` for complete sensor configuration.

## Documentation

For detailed documentation, see:
- [Addon README](coned-scraper/README.md) - Complete addon documentation
- [Home Assistant Config](coned-scraper/home-assistant-config.yaml) - Sensor configuration example

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
