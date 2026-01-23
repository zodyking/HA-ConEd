#!/bin/bash
# Home Assistant addon startup script

# Set environment variables from Home Assistant addon options
if [ -f /data/options.json ]; then
    export MQTT_HOST=$(jq -r '.mqtt_host // "core-mosquitto"' /data/options.json)
    export MQTT_PORT=$(jq -r '.mqtt_port // 1883' /data/options.json)
    export MQTT_USER=$(jq -r '.mqtt_user // ""' /data/options.json)
    export MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' /data/options.json)
    export MQTT_TOPIC_PREFIX=$(jq -r '.mqtt_topic_prefix // "coned"' /data/options.json)
fi

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
exec python -m uvicorn python-service.main:app --host 0.0.0.0 --port 8000

