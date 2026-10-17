"""Price usage-calendar days with each billing period's actual rate."""

from datetime import date, datetime
from typing import Any, Optional


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _as_positive(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def resolve_period_rate(period: dict) -> Optional[float]:
    """Actual all-in $/kWh for one billed period.

    Uses the stored kwh_cost when present. That value is electricity
    total ÷ kWh (supply, delivery, and the taxes/fees in that total).
    If it was never stored, apply the same bill formula as pdf_parser:
    electricity total ÷ kWh, else billing-period total ÷ kWh, else
    amount due ÷ kWh. No forecast or flat current rate is used.
    """
    stored = _as_positive(period.get("kwh_cost"))
    if stored is not None:
        return stored
    kwh_used = _as_positive(period.get("kwh_used"))
    total = (
        _as_positive(period.get("electricity_total"))
        or _as_positive(period.get("total_from_billing_period"))
        or _as_positive(period.get("total_amount_due"))
    )
    if kwh_used and total:
        return round(total / kwh_used, 4)
    return None


def _range_label(start: date, end: date) -> str:
    return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}"


def _usable_periods(day: date, periods: list) -> list:
    usable = []
    for period in periods or []:
        start = _as_date(period.get("start") or period.get("billing_period_start"))
        end = _as_date(period.get("end") or period.get("billing_period_end"))
        rate = resolve_period_rate(period)
        if start is None or end is None or rate is None or start > end:
            continue
        if start <= day <= end:
            label = period.get("label") or _range_label(start, end)
            usable.append({
                "bill_id": period.get("bill_id"),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": str(label),
                "range_label": _range_label(start, end),
                "kwh_cost": rate,
            })
    usable.sort(key=lambda item: (item["start"], item["end"], item["bill_id"] or 0))
    return usable


def price_day_kwh(day: date, kwh: float, periods: list) -> dict:
    """Price one US Eastern calendar day's kWh.

    Apportionment: billing periods are inclusive calendar dates. Meter
    intervals are already summed to that day, and a period has no
    time-of-day boundary, so a day covered by N billed periods splits
    its kWh into N equal shares. Each share is priced with that
    period's own rate. A day inside one period uses that rate for the
    whole day. A day outside every billed period is left unpriced.
    """
    try:
        kwh_f = float(kwh or 0)
    except (TypeError, ValueError):
        kwh_f = 0.0
    if kwh_f < 0:
        kwh_f = 0.0

    usable = _usable_periods(day, periods)
    if not usable:
        return {"cost": None, "kwh_cost": None, "rate_shares": []}

    share_kwh = kwh_f / len(usable)
    rate_shares = []
    raw_cost = 0.0
    for period in usable:
        raw_cost += share_kwh * period["kwh_cost"]
        rate_shares.append({**period, "kwh": round(share_kwh, 4)})

    cost = round(raw_cost, 2)
    # One covering period: report that bill's rate. A split day has
    # more than one real rate, so do not collapse them into a blend.
    kwh_cost = usable[0]["kwh_cost"] if len(usable) == 1 else None
    return {"cost": cost, "kwh_cost": kwh_cost, "rate_shares": rate_shares}


def price_calendar_days(days: list, periods: list) -> list:
    """Return a new list of day rows with period cost fields added."""
    priced = []
    for row in days or []:
        day = _as_date((row or {}).get("date"))
        kwh = (row or {}).get("kwh") or 0
        if day is None:
            costs = {"cost": None, "kwh_cost": None, "rate_shares": []}
        else:
            costs = price_day_kwh(day, kwh, periods)
        priced.append({**(row or {}), **costs})
    return priced
