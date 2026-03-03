"""Config flow for Con Edison integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_NAME, DEFAULT_URL, CONF_ADDON_URL

_LOGGER = logging.getLogger(__name__)


class ConEdisonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Con Edison."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            addon_url = user_input[CONF_ADDON_URL].rstrip("/")
            
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(
                    f"{addon_url}/api/version",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        await self.async_set_unique_id(addon_url)
                        self._abort_if_unique_id_configured()
                        
                        return self.async_create_entry(
                            title=DEFAULT_NAME,
                            data={CONF_ADDON_URL: addon_url},
                        )
                    else:
                        errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDON_URL, default=DEFAULT_URL): str,
                }
            ),
            errors=errors,
        )
