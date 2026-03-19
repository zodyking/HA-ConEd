# Addon Installs a Companion Integration: Benefits and Setup

An addon can ship and install a custom integration into Home Assistant. This gives the addon a native HA presence: config flow, sensors, and event handling, without users manually copying files.

## Benefits

**Unified experience.** The addon and integration share one install. Users add the addon; the integration appears as an option in Devices & services. No separate HACS or manual custom_components setup.

**Event and service access.** The integration runs inside HA core. It can listen to `hass.bus` events (e.g. `mobile_app_notification_action` for notification taps), call services, and use coordinators. The addon stays a simple API server; the integration handles HA-specific wiring. This avoids requiring users to create automations for common flows.

**Version alignment.** The integration is bundled in the addon image. When the addon updates, the integration is overwritten on next start. Users always get the integration version that matches the addon.

**Single configuration.** Users configure the addon URL once in the integration config flow. The integration uses that URL for all addon API calls.

## Setup: Auto Install on Addon Start

Add an init script that runs before your main service. Use the S6 overlay so this script completes before the API starts.

1. **Add `homeassistant_config:rw` to the addon `map`** in `config.yaml`:
```yaml
map:
  - addon_config:rw
  - homeassistant_config:rw
```

2. **Bundle the integration in the addon image.** In your Dockerfile, copy the integration source into the image:
```dockerfile
COPY integration/ /app/integration/
```

3. **Create an init script** (e.g. `rootfs/etc/s6-overlay/s6-rc.d/init-coned/run`):
```bash
#!/command/with-contenv bashio
INTEGRATION_SRC="/app/integration/coned_connect"
INTEGRATION_DST="/homeassistant/custom_components/coned_connect"

if [ -d "$INTEGRATION_SRC" ]; then
    bashio::log.info "Installing integration..."
    mkdir -p /homeassistant/custom_components
    rm -rf "$INTEGRATION_DST"
    cp -r "$INTEGRATION_SRC" "$INTEGRATION_DST"
    bashio::log.info "Integration installed to $INTEGRATION_DST"
fi
```

4. **Order services so init runs first.** The init service must complete before the API. In S6, use an `up` file that lists dependencies so the API service waits for init.

5. **Make the script executable** in the Dockerfile:
```dockerfile
RUN chmod +x /etc/s6-overlay/s6-rc.d/init-coned/run
```

Each addon start: `rm -rf` plus `cp -r` ensures a clean copy. No stale files from previous versions.

## On Addon Removal

The Supervisor does not run addon code when an addon is uninstalled. The integration files in `custom_components` are not deleted automatically. They remain until the user removes the integration from Devices & services and deletes `custom_components/<integration_name>`, or until another addon overwrites that path.

Users who uninstall the addon should remove the integration from Devices & services. The integration will fail to connect anyway once the addon is gone.

## Integration Design

The integration should:

- Use a config flow that asks for the addon URL (e.g. `http://xxx-addon-slug:8000` or the internal Docker hostname).
- Validate the URL by calling an addon health/version endpoint.
- Poll the addon API (coordinator) for sensor data.
- Register event listeners when needed (e.g. for notification actions) and forward events to the addon API.
- Use `call_soon_threadsafe` when scheduling work from event callbacks that may run off the main loop.

Place the integration in a folder like `integration/<domain>/` in the addon repo, mirroring the standard `custom_components/<domain>/` layout (manifest.json, __init__.py, config_flow.py, etc.).
