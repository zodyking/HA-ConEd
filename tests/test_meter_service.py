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


def make_service(
    selected_account_id: str = "second",
    enabled_account_ids: list[str] | None = None,
) -> MeterService:
    service = MeterService()
    service.config = {
        "email": "user@example.com",
        "password": "plain:secret",
        "totp_secret": "totp",
        "selected_account_id": selected_account_id,
        "enabled_account_ids": enabled_account_ids or [],
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


def test_enabled_accounts_filters_service_addresses_from_one_login():
    service = make_service("first", ["first", "third"])
    accounts = [
        make_account("first"),
        make_account("second"),
        make_account("third"),
    ]

    assert [account.id for account in service._enabled_accounts(accounts)] == [
        "first",
        "third",
    ]


@pytest.mark.asyncio
async def test_login_reuses_authenticated_opower_session():
    service = make_service()
    service._opower = SimpleNamespace(
        access_token="existing-token",
        async_login=AsyncMock(),
    )

    assert await service._login() is True
    service._opower.async_login.assert_not_awaited()


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
    pending = SimpleNamespace(
        start_time=datetime(2026, 8, 9, 1, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 9, 2, tzinfo=timezone.utc),
        consumption=float("nan"),
    )
    service._opower = SimpleNamespace(
        async_get_cost_reads=AsyncMock(return_value=[latest, pending])
    )
    save_reading = AsyncMock()
    monkeypatch.setitem(
        sys.modules,
        "db",
        SimpleNamespace(
            save_meter_reading_db=save_reading,
            save_meter_reading_for_account_db=AsyncMock(),
        ),
    )

    reading = await service.fetch_reading()

    assert service._opower.async_get_cost_reads.await_args.args[0] is second
    assert reading["account_id"] == "second"
    assert reading["value"] == 1.25
    assert reading["end_time"] == latest.end_time.isoformat()
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
        SimpleNamespace(
            save_meter_forecast_db=save_forecast,
            save_meter_forecast_for_account_db=AsyncMock(),
        ),
    )

    result = await service.fetch_forecast()

    assert result["account_id"] == "second"
    assert result["usage_to_date"] == 20
    save_forecast.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_all_account_data_polls_only_enabled_addresses():
    service = make_service("first", ["first", "third"])
    first, second, third = (
        make_account("first"),
        make_account("second"),
        make_account("third"),
    )
    service._login = AsyncMock(return_value=True)
    service._get_accounts = AsyncMock(return_value=[first, second, third])
    service.list_accounts = AsyncMock(
        return_value=[
            {"id": "first", "address": "TEST_SERVICE_LOCATION_ALPHA"},
            {"id": "second", "address": "TEST_SERVICE_LOCATION_BETA"},
            {"id": "third", "address": "TEST_SERVICE_LOCATION_GAMMA"},
        ]
    )
    service._opower = SimpleNamespace(async_get_forecast=AsyncMock(return_value=[]))
    service.fetch_reading = AsyncMock(
        side_effect=lambda account: {"account_id": account.id, "value": 1}
    )
    service.fetch_forecast = AsyncMock(return_value=None)

    result = await service.fetch_all_account_data()

    assert [item["id"] for item in result] == ["first", "third"]
    assert [call.args[0].id for call in service.fetch_reading.await_args_list] == [
        "first",
        "third",
    ]


@pytest.mark.asyncio
async def test_cached_account_data_returns_only_enabled_addresses(monkeypatch):
    service = make_service("first", ["first", "third"])
    first, second, third = (
        make_account("first"),
        make_account("second"),
        make_account("third"),
    )
    service._opower = SimpleNamespace()
    service._accounts = [first, second, third]
    service._account_summaries = {
        account.id: {
            "id": account.id,
            "address": f"TEST_SERVICE_LOCATION_{account.id.upper()}",
        }
        for account in service._accounts
    }
    monkeypatch.setitem(
        sys.modules,
        "db",
        SimpleNamespace(
            get_meter_readings_by_account_db=AsyncMock(
                return_value={
                    account.id: {"account_id": account.id, "value": 1}
                    for account in service._accounts
                }
            ),
            get_meter_forecasts_by_account_db=AsyncMock(return_value={}),
        ),
    )

    result = await service.get_cached_account_data()

    assert [item["id"] for item in result] == ["first", "third"]


@pytest.mark.asyncio
async def test_get_account_info_tolerates_missing_optional_customer_metadata():
    service = make_service("first")
    account = SimpleNamespace(
        id="first",
        uuid="uuid-first",
        utility_account_id="utility-first",
        meter_type="ELEC",
        read_resolution="HOUR",
    )
    service._login = AsyncMock(return_value=True)
    service._get_accounts = AsyncMock(return_value=[account])
    service._opower = SimpleNamespace(
        utility=SimpleNamespace(supports_realtime_usage=lambda: False)
    )

    info = await service.get_account_info()

    assert info["account_id"] == "first"
    assert info["customer_uuid"] is None


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
