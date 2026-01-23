# Home Assistant Addon Configuration Updates

## Changes Made Per Official Documentation

Based on [Home Assistant Add-on Configuration Documentation](https://developers.home-assistant.io/docs/add-ons/configuration/), the following changes have been made:

### ✅ 1. Configuration File Format
- **Changed**: `config.json` → `config.yaml`
- **Reason**: Home Assistant addons use YAML format for configuration files
- **Location**: `coned-scraper/config.yaml`

### ✅ 2. Dockerfile Structure
- **Updated**: Uses `ARG BUILD_FROM` and `FROM $BUILD_FROM` for multi-arch support
- **Added**: Required Docker labels (`io.hass.version`, `io.hass.type`, `io.hass.arch`)
- **Added**: `build.yaml` to specify custom base images for each architecture
- **Reason**: Required for Home Assistant's build system to properly build multi-architecture images

### ✅ 3. Startup Script (run.sh)
- **Updated**: Uses `bashio` for configuration parsing (with jq fallback)
- **Format**: Follows Home Assistant addon script conventions
- **Reason**: bashio is the standard way to parse options in Home Assistant addons

### ✅ 4. Schema Validation
- **Updated**: Uses proper schema types (`port`, `password?`, `int(min,)`)
- **Reason**: Ensures proper validation of user input in the Home Assistant UI

### ✅ 5. Architecture Support
- **Verified**: All required architectures listed: `aarch64`, `amd64`, `armhf`, `armv7`, `i386`
- **Reason**: Matches Home Assistant's supported architectures

## File Structure (Per Documentation)

```
coned-scraper/
├── config.yaml          # ✅ Addon configuration (YAML format)
├── Dockerfile           # ✅ Uses BUILD_FROM for multi-arch
├── build.yaml          # ✅ Custom base images per architecture
├── run.sh              # ✅ Uses bashio for config parsing
├── README.md           # ✅ Addon documentation
├── home-assistant-config.yaml  # ✅ HA sensor config example
└── python-service/     # ✅ Application code
    ├── main.py
    ├── browser_automation.py
    ├── database.py
    ├── mqtt_client.py
    ├── change_detection.py
    ├── sensor_publisher.py
    └── requirements.txt
```

## Key Compliance Points

1. ✅ **config.yaml** uses YAML format (not JSON)
2. ✅ **Dockerfile** uses `ARG BUILD_FROM` and `FROM $BUILD_FROM`
3. ✅ **Dockerfile** includes required labels
4. ✅ **build.yaml** specifies base images per architecture
5. ✅ **run.sh** uses bashio for configuration (with fallback)
6. ✅ **Schema** uses proper validation types
7. ✅ **Architecture** list matches Home Assistant requirements

## Next Steps

1. Push updated files to GitHub
2. Remove and re-add repository in Home Assistant
3. Try installing the addon again

The addon should now comply with Home Assistant's official addon structure requirements.

