"""The Con Edison integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_ADDON_URL
from .coordinator import ConEdisonDataUpdateCoordinator

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


def _create_payment_claim_handler(hass: HomeAssistant, addon_url: str) -> Callable[[Event], None]:
    """Create a callback that forwards CONED_CLAIM_* events to the addon."""

    def handler(event: Event) -> None:
        action = event.data.get("action") or ""
        if not action.startswith("CONED_CLAIM_"):
            return

        async def _post() -> None:
            session = async_get_clientsession(hass)
            url = f"{addon_url.rstrip('/')}/api/payments/claim-action"
            try:
                async with session.post(
                    url,
                    json={"action": action},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        _LOGGER.warning(
                            "Payment claim request failed: %s %s",
                            resp.status,
                            await resp.text(),
                        )
            except Exception as err:
                _LOGGER.warning("Payment claim request error: %s", err)

        hass.async_create_task(_post())

    return handler


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Con Edison from a config entry."""
    addon_url = entry.data[CONF_ADDON_URL]

    coordinator = ConEdisonDataUpdateCoordinator(hass, addon_url)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    handler = _create_payment_claim_handler(hass, addon_url)
    unsub_mobile = hass.bus.async_listen("mobile_app_notification_action", handler)
    unsub_ios = hass.bus.async_listen("ios.notification_action", handler)
    hass.data[DOMAIN][f"_unsub_{entry.entry_id}"] = [unsub_mobile, unsub_ios]

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unsubs = hass.data.get(DOMAIN, {}).pop(f"_unsub_{entry.entry_id}", [])
    for unsub in unsubs:
        unsub()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
