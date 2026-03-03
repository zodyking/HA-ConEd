"""Sensor platform for Con Edison integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSORS
from .coordinator import ConEdisonDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Con Edison sensors from a config entry."""
    coordinator: ConEdisonDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ConEdisonSensor(coordinator, entry, sensor_type)
        for sensor_type in SENSORS
    ]
    
    async_add_entities(entities)


class ConEdisonSensor(CoordinatorEntity[ConEdisonDataUpdateCoordinator], SensorEntity):
    """Representation of a Con Edison sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ConEdisonDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_type = sensor_type
        self._sensor_config = SENSORS[sensor_type]
        
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = self._sensor_config["name"]
        self._attr_native_unit_of_measurement = self._sensor_config.get("unit")
        self._attr_icon = self._sensor_config.get("icon")
        
        device_class = self._sensor_config.get("device_class")
        if device_class == "monetary":
            self._attr_device_class = SensorDeviceClass.MONETARY
        elif device_class == "energy":
            self._attr_device_class = SensorDeviceClass.ENERGY
        else:
            self._attr_device_class = None
        
        state_class = self._sensor_config.get("state_class")
        if state_class == "total_increasing":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif state_class == "total":
            self._attr_state_class = SensorStateClass.TOTAL
        elif state_class == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_state_class = None
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Con Edison",
            manufacturer="HA-ConEd",
            model="Con Edison Account",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(self._sensor_type)
        
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            if self._sensor_config.get("device_class") == "monetary":
                return round(value, 2)
            elif self._sensor_config.get("device_class") == "energy":
                return round(value, 2)
            elif self._sensor_type == "kwh_cost":
                return round(value, 4)
            return value
        
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None
        
        data_key = f"{self._sensor_type}_data"
        extra_data = self.coordinator.data.get(data_key)
        
        if extra_data and isinstance(extra_data, dict):
            return extra_data
        
        return None
