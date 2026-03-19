# Communicating from Addon to Home Assistant: MQTT vs Registered Integration

When an addon needs to push data or events into Home Assistant, two common approaches are MQTT and a companion integration. Each has tradeoffs.

## MQTT

The addon publishes to an MQTT broker (e.g. Mosquitto). Home Assistant subscribes to topics. MQTT discovery lets the addon publish JSON configs so sensors appear automatically without YAML.

**Pros:**
- Decoupled. The addon does not need `homeassistant_api` or Supervisor access. It only needs broker credentials.
- Works when the addon runs outside HA (dev, different host). Publish to a broker; HA picks it up regardless of where the addon runs.
- Standard protocol. Any MQTT client can subscribe. Easy to debug with external tools.
- Discovery avoids manual YAML. Publish discovery payloads; sensors register under Devices & services → MQTT.

**Cons:**
- Requires MQTT broker configuration in the addon. Users must set URL, credentials, base topic.
- One-way. Addon pushes; it does not receive HA events or call HA services directly. For actions (e.g. TTS, automations) you must either publish to a topic and add an HA automation to handle it, or use a different channel.
- Duplicates and stale sensors. Retained discovery messages can cause duplicates if topics change. You need cleanup logic (empty retained messages) to remove old sensors.
- No access to HA internals. The addon cannot listen to `hass.bus` events (e.g. `mobile_app_notification_action`), use `hass.loop`, or call HA services without `homeassistant_api`.

## Companion Integration

The addon ships an integration and installs it into `custom_components` on startup. The integration runs inside HA core and polls the addon's HTTP API or listens to events.

**Pros:**
- Native HA integration. Appears in Devices & services. Has config flow. Can expose sensors, listen to events, call services.
- Direct access to HA APIs. Can use `hass.bus.async_listen`, `hass.services`, coordinator patterns. Event-driven flows (e.g. notification taps) work without automations.
- No MQTT broker setup. Users add the integration, enter the addon URL, done. No extra infrastructure.
- Clean lifecycle. Integration is part of the addon. When the addon updates, the integration is overwritten on next start.

**Cons:**
- Requires addon to be running. The integration calls the addon URL. If the addon is stopped or unreachable, sensors and features fail.
- Write access to HA config. The addon needs `homeassistant_config:rw` to copy files into `custom_components`. Not all addons have this.
- One-time setup. User must add the integration (config flow) and configure the addon URL. More steps than "just enable MQTT."
- Tied to HA. The integration only runs inside HA. It cannot run standalone or on another host.

## When to Use Which

Use MQTT when: the addon must work without Supervisor, runs on another machine, or needs to publish data without touching HA config. Use it for sensors and one-way publish; add automations for actions.

Use an integration when: the addon runs as a Supervisor addon and you need event handling (e.g. notification actions), direct service calls, or native config flow. The integration is the bridge from HA's event loop to your addon API.

A hybrid is common: MQTT for sensors (especially if users already have MQTT), integration for features that require HA event or service access.
