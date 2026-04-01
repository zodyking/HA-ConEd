"""Data coordinator for Con Edison integration."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

ADDON_SLUG = "9a4bbad0_coned_scraper"


def extract_numeric(value: str | float | int | None) -> float:
    """Extract numeric value from string (e.g., '$123.45' -> 123.45)."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.-]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class ConEdisonDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Con Edison data from the addon API."""

    def __init__(self, hass: HomeAssistant, addon_url: str) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.addon_url = addon_url.rstrip("/")
        self.hass = hass
        self._ingress_url: str | None = None

    async def _get_ingress_url(self) -> str | None:
        """Get the Ingress URL for the addon from Supervisor API."""
        if self._ingress_url:
            return self._ingress_url
        
        token = os.environ.get("SUPERVISOR_TOKEN")
        if not token:
            return None
        
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"http://supervisor/addons/{ADDON_SLUG}/info",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    info = await response.json()
                    data = info.get("data", {})
                    ingress_entry = data.get("ingress_entry")
                    if ingress_entry:
                        self._ingress_url = ingress_entry
                        _LOGGER.debug("Got ingress entry: %s", ingress_entry)
                        return ingress_entry
        except Exception as err:
            _LOGGER.debug("Failed to get ingress URL: %s", err)
        
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the addon API."""
        try:
            session = async_get_clientsession(self.hass)
            data: dict[str, Any] = {}

            # Fetch ledger data (account_balance, bills, payments)
            async with session.get(
                f"{self.addon_url}/api/ledger",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    ledger = await response.json()
                    data["account_balance"] = extract_numeric(
                        ledger.get("account_balance")
                    )
                    
                    bills = ledger.get("bills", [])
                    if len(bills) > 0:
                        latest = bills[0]
                        data["latest_bill"] = extract_numeric(latest.get("bill_total"))
                        data["latest_bill_data"] = latest
                    if len(bills) >= 2:
                        data["previous_bill"] = extract_numeric(bills[1].get("bill_total"))
                        data["previous_bill_data"] = bills[1]
                    
                    # Get last payment: use addon's latest_payment (most recent for current bill)
                    latest_payment = ledger.get("latest_payment")
                    if latest_payment and isinstance(latest_payment, dict):
                        data["last_payment"] = extract_numeric(
                            latest_payment.get("amount")
                        )
                        data["last_payment_data"] = latest_payment
                    elif bills and bills[0].get("payments"):
                        # Fallback: first item = most recent (addon sorts payments desc)
                        payments = bills[0]["payments"]
                        if payments:
                            last_payment = payments[0]
                            data["last_payment"] = extract_numeric(
                                last_payment.get("amount")
                            )
                            data["last_payment_data"] = last_payment
                    
            # Fetch bill details (due_date, kwh_cost, kwh_used)
            async with session.get(
                f"{self.addon_url}/api/bill-details/latest",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    details = await response.json()
                    data["due_date"] = details.get("due_date")
                    data["kwh_cost"] = details.get("kwh_cost")
                    data["last_bill_kwh"] = details.get("kwh_used")

            # Fetch meter reading data (current usage, forecast)
            async with session.get(
                f"{self.addon_url}/api/meter-reading",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    meter = await response.json()
                    data["current_usage_cost"] = meter.get("cost")
                    
                    forecast = meter.get("forecast", {})
                    if forecast:
                        data["billing_start_date"] = forecast.get("start_date")
                        data["billing_end_date"] = forecast.get("end_date")
                        data["current_cycle_usage"] = forecast.get("usage_to_date")
                        data["forecasted_usage"] = forecast.get("forecasted_usage")

            # Fetch bill PDF URL - check if PDF exists first
            async with session.get(
                f"{self.addon_url}/api/bill-document",
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if response.status == 200:
                    # PDF exists - construct external Ingress URL (full URL in attributes only)
                    ingress_entry = await self._get_ingress_url()
                    if ingress_entry:
                        base_url = get_url(self.hass, prefer_external=True, require_ssl=False)
                        pdf_url = f"{base_url.rstrip('/')}{ingress_entry}/api/bill-document"
                    else:
                        pdf_url = f"{self.addon_url}/api/bill-document"
                    data["bill_pdf_url"] = "Check attributes"
                    data["bill_pdf_url_data"] = {"url": pdf_url}

            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with addon: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
