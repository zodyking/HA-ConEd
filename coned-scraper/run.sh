#!/bin/bash
# Home Assistant addon startup script

set -e

# Parse configuration options using jq (bashio not available in custom base image)
if [ -f /data/options.json ]; then
    MQTT_HOST=$(jq -r '.mqtt_host // "core-mosquitto"' /data/options.json)
    MQTT_PORT=$(jq -r '.mqtt_port // 1883' /data/options.json)
    MQTT_USER=$(jq -r '.mqtt_user // ""' /data/options.json)
    MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' /data/options.json)
    MQTT_TOPIC_PREFIX=$(jq -r '.mqtt_topic_prefix // "coned"' /data/options.json)
else
    # Default values if no config file
    MQTT_HOST="core-mosquitto"
    MQTT_PORT=1883
    MQTT_USER=""
    MQTT_PASSWORD=""
    MQTT_TOPIC_PREFIX="coned"
fi

# Export environment variables
export MQTT_HOST
export MQTT_PORT
export MQTT_USER
export MQTT_PASSWORD
export MQTT_TOPIC_PREFIX

# Link data directory to persistent storage
if [ ! -d /app/python-service/data ]; then
    mkdir -p /app/python-service/data
fi

# Copy credentials if they exist in persistent storage
if [ -f /data/credentials.json ]; then
    cp /data/credentials.json /app/python-service/data/ 2>/dev/null || true
fi

if [ -f /data/.key ]; then
    cp /data/.key /app/python-service/data/ 2>/dev/null || true
fi

# Start the application
cd /app
exec python3 -m uvicorn python-service.main:app --host 0.0.0.0 --port 8000
