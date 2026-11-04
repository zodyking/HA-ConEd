"""Adopt leftover MQTT sensors so ConEd Connect unique_ids match auto-install."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, SENSORS, mqtt_unique_id

_LOGGER = logging.getLogger(__name__)


def _object_id(entity_id: str) -> str:
    return entity_id.split(".", 1)[-1] if entity_id else ""


def _mqtt_matches(entry: Any, sensor_type: str) -> bool:
    if entry.domain != "sensor" or entry.platform != "mqtt":
        return False
    uid = entry.unique_id or ""
    target = mqtt_unique_id(sensor_type)
    if uid == target or uid.startswith(f"{target}_"):
        return True
    slug = sensor_type.lower()
    object_id = _object_id(entry.entity_id)
    if object_id == f"coned_{slug}":
        return True
    if object_id.endswith(f"_coned_{slug}"):
        return True
    return bool(re.search(rf"(?:^|_)coned_{re.escape(slug)}_\d+$", object_id))


def adopt_mqtt_unique_ids(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Remove leftover MQTT sensors and migrate old ConEd Connect unique_ids.

    Returns a map of sensor_type -> entity_id to reuse so dashboards keep working.
    """
    registry = er.async_get(hass)
    adopted: dict[str, str] = {}

    for sensor_type in SENSORS:
        uid = mqtt_unique_id(sensor_type)
        mqtt_matches = [
            item
            for item in list(registry.entities.values())
            if _mqtt_matches(item, sensor_type)
        ]
        mqtt_matches.sort(key=lambda item: (item.entity_id.count("_"), item.entity_id))
        mqtt_eid = mqtt_matches[0].entity_id if mqtt_matches else None
        for item in mqtt_matches:
            registry.async_remove(item.entity_id)
            _LOGGER.info(
                "Removed leftover MQTT sensor %s so ConEd Connect can update %s",
                item.entity_id,
                uid,
            )

        old_eid = registry.async_get_entity_id("sensor", DOMAIN, f"{entry_id}_{sensor_type}")
        if old_eid:
            registry.async_update_entity(old_eid, new_unique_id=uid)
            _LOGGER.info("Migrated ConEd Connect unique_id for %s to %s", old_eid, uid)

        existing = registry.async_get_entity_id("sensor", DOMAIN, uid)
        if existing:
            # Keep the live ConEd Connect entity_id; unique_id matching is enough.
            continue
        if mqtt_eid:
            adopted[sensor_type] = mqtt_eid

    return adopted
