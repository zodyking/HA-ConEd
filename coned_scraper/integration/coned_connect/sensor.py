"""Sensor platform for Con Edison integration."""
from __future__ import annotations

import hashlib
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

from .const import ACCOUNT_SENSORS, DOMAIN, SENSORS
from .coordinator import ConEdisonDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Con Edison sensors from a config entry."""
    coordinator: ConEdisonDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities: list[SensorEntity] = [
        ConEdisonSensor(coordinator, entry, sensor_type)
        for sensor_type in SENSORS
    ]
    async_add_entities(entities)

    known_account_ids: set[str] = set()

    def add_account_entities() -> None:
        """Add devices and sensors for newly enabled service addresses."""
        accounts = (coordinator.data or {}).get("meter_accounts", [])
        new_entities: list[SensorEntity] = []
        for account in accounts:
            account_id = str(account.get("id", "") or "").strip()
            if not account_id or account_id in known_account_ids:
                continue
            known_account_ids.add(account_id)
            new_entities.extend(
                ConEdisonAccountSensor(
                    coordinator, entry, account_id, sensor_type, account
                )
                for sensor_type in ACCOUNT_SENSORS
            )
        if new_entities:
            async_add_entities(new_entities)

    add_account_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_account_entities))


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
            name="ConEd Connect",
            manufacturer="HA-ConEd",
            model="ConEd Connect Account",
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


class ConEdisonAccountSensor(
    CoordinatorEntity[ConEdisonDataUpdateCoordinator], SensorEntity
):
    """A meter sensor scoped to one enabled Con Edison service address."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ConEdisonDataUpdateCoordinator,
        entry: ConfigEntry,
        account_id: str,
        sensor_type: str,
        account: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._sensor_type = sensor_type
        self._sensor_config = ACCOUNT_SENSORS[sensor_type]
        account_key = hashlib.sha256(account_id.encode()).hexdigest()[:12]
        account_label = (
            account.get("address")
            or account.get("account_name")
            or account.get("account_number")
            or f"Electric Account {account_key[:4]}"
        )

        self._attr_unique_id = f"{entry.entry_id}_{account_key}_{sensor_type}"
        self._attr_name = self._sensor_config["name"]
        self._attr_native_unit_of_measurement = self._sensor_config.get("unit")
        self._attr_icon = self._sensor_config.get("icon")

        device_class = self._sensor_config.get("device_class")
        if device_class == "monetary":
            self._attr_device_class = SensorDeviceClass.MONETARY
        elif device_class == "energy":
            self._attr_device_class = SensorDeviceClass.ENERGY

        state_class = self._sensor_config.get("state_class")
        if state_class == "total":
            self._attr_state_class = SensorStateClass.TOTAL
        elif state_class == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{account_key}")},
            name=f"ConEd Meter - {account_label}",
            manufacturer="HA-ConEd",
            model="ConEd Electric Service Address",
        )

    def _account_data(self) -> dict[str, Any] | None:
        for account in (self.coordinator.data or {}).get("meter_accounts", []):
            if str(account.get("id", "") or "") == self._account_id:
                return account
        return None

    @property
    def available(self) -> bool:
        """Mark sensors unavailable when their address is no longer enabled."""
        return super().available and self._account_data() is not None

    @property
    def native_value(self) -> Any:
        account = self._account_data()
        if not account:
            return None
        source = self._sensor_config.get("source", self._sensor_type)
        value = account.get(source)
        if isinstance(value, (int, float)):
            if self._sensor_config.get("device_class") == "monetary":
                return round(value, 2)
            if self._sensor_config.get("device_class") == "energy":
                return round(value, 3)
            if self._sensor_type == "kwh_cost":
                return round(value, 4)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return local display metadata without exposing raw account IDs."""
        account = self._account_data()
        if not account:
            return None
        reading = account.get("reading") or {}
        return {
            "service_address": account.get("address") or None,
            "account_name": account.get("account_name") or None,
            "account_type": account.get("account_type") or None,
            "account_number": account.get("account_number") or None,
            "reading_end_time": reading.get("end_time"),
            "reading_fetched_at": reading.get("fetched_at"),
        }
