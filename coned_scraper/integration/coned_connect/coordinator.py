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

    async def _fetch_json(self, session: aiohttp.ClientSession, path: str, timeout: int = 30) -> Any:
        """GET JSON from the addon. A failed call returns None instead of aborting the rest."""
        try:
            async with session.get(
                f"{self.addon_url}{path}",
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 200:
                    return await response.json()
                _LOGGER.debug("Addon %s returned %s", path, response.status)
        except Exception as err:
            _LOGGER.warning("Addon %s failed: %s", path, err)
        return None

    async def _attach_pdf_url(self, session: aiohttp.ClientSession, data: dict[str, Any]) -> None:
        """Fill bill_pdf_url without failing the rest of the update."""
        try:
            async with session.get(
                f"{self.addon_url}/api/bill-document",
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    return
                ingress_entry = await self._get_ingress_url()
                if ingress_entry:
                    base_url = get_url(self.hass, prefer_external=True, require_ssl=False)
                    pdf_url = f"{base_url.rstrip('/')}{ingress_entry}/api/bill-document"
                else:
                    pdf_url = f"{self.addon_url}/api/bill-document"
                data["bill_pdf_url"] = "Check attributes"
                data["bill_pdf_url_data"] = {"url": pdf_url}
        except Exception as err:
            _LOGGER.debug("Bill PDF URL unavailable: %s", err)

    def _merge_legacy_payloads(
        self,
        ledger: dict[str, Any] | None,
        details: dict[str, Any] | None,
        meter: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Map older addon endpoints when /api/ha-sensors is missing."""
        data: dict[str, Any] = {}
        if ledger:
            data["account_balance"] = extract_numeric(ledger.get("account_balance"))
            bills = ledger.get("bills", [])
            if len(bills) > 0:
                latest = bills[0]
                data["latest_bill"] = extract_numeric(latest.get("bill_total"))
                data["latest_bill_data"] = latest
            if len(bills) >= 2:
                data["previous_bill"] = extract_numeric(bills[1].get("bill_total"))
                data["previous_bill_data"] = bills[1]
            latest_payment = ledger.get("latest_payment")
            if latest_payment and isinstance(latest_payment, dict):
                data["last_payment"] = extract_numeric(latest_payment.get("amount"))
                data["last_payment_data"] = latest_payment
            elif bills and bills[0].get("payments"):
                payments = bills[0]["payments"]
                if payments:
                    last_payment = payments[0]
                    data["last_payment"] = extract_numeric(last_payment.get("amount"))
                    data["last_payment_data"] = last_payment
            summaries = ledger.get("payee_summaries") or {}
            latest_id = bills[0].get("id") if bills else None
            summary = None
            if isinstance(summaries, dict) and latest_id is not None:
                summary = summaries.get(latest_id) or summaries.get(str(latest_id))
            if summary:
                payees = summary.get("payee_summaries") or summary.get("payees") or []
                by_id = {
                    str(payee.get("user_id") if payee.get("user_id") is not None else payee.get("id")): payee
                    for payee in payees
                    if payee.get("user_id") is not None or payee.get("id") is not None
                }
                data["payee_summary"] = extract_numeric(summary.get("bill_balance"))
                data["payee_summary_data"] = {
                    "bill_cycle_date": summary.get("bill_cycle_date") or "",
                    "bill_total": extract_numeric(summary.get("bill_total")),
                    "total_paid": extract_numeric(summary.get("total_paid")),
                    "bill_balance": extract_numeric(summary.get("bill_balance")),
                    "bill_status": summary.get("bill_status") or "unknown",
                    "month_range": summary.get("month_range") or "",
                    "payees": payees,
                    "payee_names": [payee.get("name") for payee in payees if payee.get("name")],
                    "payees_by_id": by_id,
                }
        if details:
            data["due_date"] = details.get("due_date")
            data["kwh_cost"] = details.get("kwh_cost")
            data["last_bill_kwh"] = details.get("kwh_used")
        if meter:
            usage_cost = meter.get("usage_to_date_cost")
            if usage_cost is None:
                usage_cost = meter.get("cost")
            data["current_usage_cost"] = usage_cost
            reading = meter.get("reading") or {}
            if isinstance(reading, dict):
                data["current_meter_usage"] = reading.get("value")
            forecast = meter.get("forecast") or {}
            if forecast:
                data["billing_start_date"] = forecast.get("start_date")
                data["billing_end_date"] = forecast.get("end_date")
                data["current_cycle_usage"] = forecast.get("usage_to_date")
                data["forecasted_usage"] = forecast.get("forecasted_usage")
        return data

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the addon API. One failed endpoint must not stale the rest."""
        session = async_get_clientsession(self.hass)
        data: dict[str, Any] = {}

        bundled = await self._fetch_json(session, "/api/ha-sensors")
        if isinstance(bundled, dict) and bundled:
            data.update(bundled)
        else:
            ledger, details, meter = await _gather_legacy(self, session)
            data.update(self._merge_legacy_payloads(ledger, details, meter))

        await self._attach_pdf_url(session, data)

        if not data:
            raise UpdateFailed("Addon returned no sensor data")
        return data


async def _gather_legacy(
    coordinator: ConEdisonDataUpdateCoordinator,
    session: aiohttp.ClientSession,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    ledger = await coordinator._fetch_json(session, "/api/ledger")
    details = await coordinator._fetch_json(session, "/api/bill-details/latest")
    meter = await coordinator._fetch_json(session, "/api/meter-reading")
    return (
        ledger if isinstance(ledger, dict) else None,
        details if isinstance(details, dict) else None,
        meter if isinstance(meter, dict) else None,
    )
