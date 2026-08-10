import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


SERVICE_DIR = Path(__file__).parents[1] / "coned_scraper" / "python-service"
sys.path.insert(0, str(SERVICE_DIR))

from meter_service import MeterService  # noqa: E402


def make_account(account_id: str, meter_type: str = "ELEC") -> SimpleNamespace:
    return SimpleNamespace(
        id=account_id,
        uuid=f"uuid-{account_id}",
        utility_account_id=f"utility-{account_id}",
        meter_type=meter_type,
        read_resolution="HOUR",
        customer=SimpleNamespace(uuid=f"customer-{account_id}"),
    )


def make_service(selected_account_id: str = "second") -> MeterService:
    service = MeterService()
    service.config = {
        "email": "user@example.com",
        "password": "plain:secret",
        "totp_secret": "totp",
        "selected_account_id": selected_account_id,
    }
    return service


def test_select_account_uses_configured_stable_id():
    service = make_service()
    accounts = [make_account("first"), make_account("second")]

    assert service._select_account(accounts) is accounts[1]


def test_select_account_preserves_legacy_first_account_default():
    service = make_service("")
    accounts = [make_account("first"), make_account("second")]

    assert service._select_account(accounts) is accounts[0]


@pytest.mark.asyncio
async def test_list_accounts_filters_gas_and_includes_customer_labels():
    service = make_service()
    electric = make_account("electric")
    gas = make_account("gas", "GAS")
    service._login = AsyncMock(return_value=True)
    service._get_accounts = AsyncMock(return_value=[electric, gas])
    service._opower = SimpleNamespace(
        _async_get_customers=AsyncMock(
            return_value=[
                {
                    "uuid": electric.customer.uuid,
                    "accountName": "Home",
                    "accountNumber": "1234567890",
                    "type": "Residential",
                    "address": "TEST_SERVICE_LOCATION_ALPHA",
                }
            ]
        )
    )

    accounts = await service.list_accounts()

    assert [account["id"] for account in accounts] == ["electric"]
    assert accounts[0]["address"] == "TEST_SERVICE_LOCATION_ALPHA"
    assert accounts[0]["account_number"].endswith("7890")
    assert "123456" not in accounts[0]["account_number"]


@pytest.mark.asyncio
async def test_fetch_reading_uses_selected_account(monkeypatch):
    service = make_service()
    first, second = make_account("first"), make_account("second")
    service._login = AsyncMock(return_value=True)
    service._get_accounts = AsyncMock(return_value=[first, second])
    latest = SimpleNamespace(
        start_time=datetime(2026, 8, 9, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 9, 1, tzinfo=timezone.utc),
        consumption=1.25,
    )
    service._opower = SimpleNamespace(
        async_get_cost_reads=AsyncMock(return_value=[latest])
    )
    save_reading = AsyncMock()
    monkeypatch.setitem(
        sys.modules,
        "db",
        SimpleNamespace(save_meter_reading_db=save_reading),
    )

    reading = await service.fetch_reading()

    assert service._opower.async_get_cost_reads.await_args.args[0] is second
    assert reading["account_id"] == "second"
    save_reading.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_forecast_filters_to_selected_account(monkeypatch):
    service = make_service()
    first, second = make_account("first"), make_account("second")
    service._login = AsyncMock(return_value=True)
    service._get_accounts = AsyncMock(return_value=[first, second])

    def forecast(account, usage):
        return SimpleNamespace(
            account=account,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            usage_to_date=usage,
            forecasted_usage=usage * 2,
            cost_to_date=10,
            forecasted_cost=20,
            unit_of_measure="KWH",
        )

    service._opower = SimpleNamespace(
        async_get_forecast=AsyncMock(
            return_value=[forecast(first, 10), forecast(second, 20)]
        )
    )
    save_forecast = AsyncMock()
    monkeypatch.setitem(
        sys.modules,
        "db",
        SimpleNamespace(save_meter_forecast_db=save_forecast),
    )

    result = await service.fetch_forecast()

    assert result["account_id"] == "second"
    assert result["usage_to_date"] == 20
    save_forecast.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_reading_from_another_account_is_ignored(monkeypatch):
    service = make_service()
    monkeypatch.setitem(
        sys.modules,
        "db",
        SimpleNamespace(
            get_meter_reading_db=AsyncMock(
                return_value={"account_id": "first", "value": 3.0}
            )
        ),
    )

    assert await service.get_cached_reading() is None
