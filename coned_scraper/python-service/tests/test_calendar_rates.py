"""Calendar days use each billing period's actual rate."""

from datetime import date

from calendar_rates import price_calendar_days, price_day_kwh, resolve_period_rate


PERIOD_A = {
    "bill_id": 1,
    "start": "2026-01-01",
    "end": "2026-01-31",
    "label": "Jan",
    "kwh_cost": 0.2511,
}
PERIOD_B = {
    "bill_id": 2,
    "start": "2026-02-01",
    "end": "2026-02-28",
    "label": "Feb",
    "kwh_cost": 0.3184,
}


def test_adjacent_periods_use_their_own_rates():
    days = [
        {"date": "2026-01-15", "kwh": 10},
        {"date": "2026-02-10", "kwh": 10},
        {"date": "2025-12-31", "kwh": 10},
    ]
    priced = {row["date"]: row for row in price_calendar_days(days, [PERIOD_A, PERIOD_B])}

    january = priced["2026-01-15"]
    february = priced["2026-02-10"]
    outside = priced["2025-12-31"]

    assert january["kwh_cost"] == 0.2511
    assert january["cost"] == round(10 * 0.2511, 2)
    assert january["rate_shares"][0]["bill_id"] == 1
    assert len(january["rate_shares"]) == 1

    assert february["kwh_cost"] == 0.3184
    assert february["cost"] == round(10 * 0.3184, 2)
    assert february["rate_shares"][0]["bill_id"] == 2

    assert january["cost"] != february["cost"]
    assert january["cost"] != round(10 * 0.3184, 2)
    assert february["cost"] != round(10 * 0.2511, 2)
    assert outside["cost"] is None
    assert outside["kwh_cost"] is None
    assert outside["rate_shares"] == []


def test_shared_boundary_day_splits_kwh_evenly():
    # Inclusive period edges meet on Feb 1. Intervals are daily totals,
    # so that day's kWh is split in half across the two real rates.
    periods = [
        {**PERIOD_A, "end": "2026-02-01"},
        PERIOD_B,
    ]
    priced = price_day_kwh(date(2026, 2, 1), 10, periods)

    assert priced["kwh_cost"] is None
    assert len(priced["rate_shares"]) == 2
    assert [share["kwh"] for share in priced["rate_shares"]] == [5.0, 5.0]
    assert [share["kwh_cost"] for share in priced["rate_shares"]] == [0.2511, 0.3184]
    assert priced["cost"] == round(5 * 0.2511 + 5 * 0.3184, 2)


def test_missing_stored_rate_uses_period_electricity_total():
    period = {
        "bill_id": 3,
        "start": "2026-03-01",
        "end": "2026-03-31",
        "kwh_cost": None,
        "kwh_used": 400,
        "electricity_total": 100,
    }
    assert resolve_period_rate(period) == 0.25
    priced = price_day_kwh(date(2026, 3, 10), 8, [period, PERIOD_B])
    assert priced["kwh_cost"] == 0.25
    assert priced["cost"] == round(8 * 0.25, 2)
