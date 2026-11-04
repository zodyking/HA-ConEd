"""Home Assistant sensor payload for ConEd Connect.

MQTT used unique_ids like ``ConEd_payee_summary``. ConEd Connect matches those
ids so leftover MQTT entities are replaced and every sensor is updated from
one addon payload.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Mapping, Optional, Sequence


def extract_numeric(value: Any) -> float:
    """Extract a dollar/kWh number from strings like '$123.45'."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.-]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _money(value: Any) -> float:
    return round(float(value or 0.0), 2)


def _payee_id(raw: Mapping[str, Any]) -> Any:
    """Configured payee id (not the display name). None when unset."""
    value = raw.get("user_id")
    if value is None:
        value = raw.get("id")
    if value is None or value == "":
        return None
    return value


def _days_owing(owing_since: Any, today: date) -> int:
    if not owing_since:
        return 0
    if isinstance(owing_since, date):
        start = owing_since
    else:
        text = str(owing_since).strip()[:10]
        try:
            start = date.fromisoformat(text)
        except ValueError:
            return 0
    return max(0, (today - start).days)


def build_payee_summary_attributes(
    summary: Optional[Mapping[str, Any]],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Generic payee attributes for whatever payees are configured.

    Each configured payee is listed with balance (signed remaining), days
    they have been owing, and how much they still need to pay. Lookup is by
    ``payees`` (ordered list) and ``payees_by_id`` (keyed by payee user id).
    Display names stay on each row; they are never used as attribute keys.
    """
    today = today or date.today()
    empty = {
        "bill_balance": 0.0,
        "bill_total": 0.0,
        "total_paid": 0.0,
        "bill_status": "unknown",
        "payees": [],
        "payee_names": [],
        "payees_by_id": {},
    }
    if not summary:
        return empty

    bill_total = _money(summary.get("bill_total"))
    total_paid = _money(summary.get("total_paid"))
    bill_balance = _money(summary.get("bill_balance"))
    attrs: Dict[str, Any] = {
        "bill_cycle_date": summary.get("bill_cycle_date") or "",
        "bill_total": bill_total,
        "total_paid": total_paid,
        "bill_balance": bill_balance,
        "bill_status": summary.get("bill_status") or "unknown",
        "month_range": summary.get("month_range") or "",
    }

    payees: List[Dict[str, Any]] = []
    names: List[str] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    raw_payees = summary.get("payees") or summary.get("payee_summaries") or []
    for raw in raw_payees:
        name = str(raw.get("name") or "Unknown")
        percent = float(raw.get("responsibility_percent") or 0)
        if percent <= 0 and abs(_money(raw.get("current_balance"))) < 0.01:
            continue
        paid = _money(raw.get("amount_paid"))
        due = _money(raw.get("amount_due") if raw.get("amount_due") is not None else raw.get("share_of_bill_cumulative"))
        remaining = _money(due - paid)
        amount_to_pay = max(0.0, remaining)
        credit = max(0.0, -remaining)
        owing_since = raw.get("owing_since") if remaining > 0.009 else None
        days_owing = _days_owing(owing_since, today) if remaining > 0.009 else 0
        status = raw.get("status") or "paid"
        row: Dict[str, Any] = {
            "name": name,
            "responsibility_percent": percent,
            "balance": remaining,
            "amount_to_pay": amount_to_pay,
            "credit": credit,
            "days_owing": days_owing,
            "amount_paid": paid,
            "amount_due": due,
            "status": status,
            "share_of_bill": _money(raw.get("share_of_bill")),
        }
        payee_id = _payee_id(raw)
        if payee_id is not None:
            row["user_id"] = payee_id
            by_id[str(payee_id)] = row
        if owing_since:
            row["owing_since"] = owing_since
        payees.append(row)
        names.append(name)

    attrs["payees"] = payees
    attrs["payee_names"] = names
    attrs["payees_by_id"] = by_id
    return attrs


def _lookup_summary(summaries: Any, bill_id: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(summaries, dict) or bill_id is None:
        return None
    if bill_id in summaries:
        return summaries[bill_id]
    return summaries.get(str(bill_id))


def map_ha_sensor_payload(
    ledger: Mapping[str, Any],
    details: Optional[Mapping[str, Any]] = None,
    meter: Optional[Mapping[str, Any]] = None,
    payee_summary: Optional[Mapping[str, Any]] = None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Build the dict ConEd Connect sensors read. Missing sources stay unset."""
    data: Dict[str, Any] = {}
    details = details or {}
    meter = meter or {}
    today = today or date.today()

    data["account_balance"] = extract_numeric(ledger.get("account_balance"))

    bills: Sequence[Mapping[str, Any]] = ledger.get("bills") or []
    if bills:
        latest = bills[0]
        data["latest_bill"] = extract_numeric(latest.get("bill_total"))
        data["latest_bill_data"] = dict(latest)
        if len(bills) >= 2:
            previous = bills[1]
            data["previous_bill"] = extract_numeric(previous.get("bill_total"))
            data["previous_bill_data"] = dict(previous)

    latest_payment = ledger.get("latest_payment")
    if isinstance(latest_payment, dict):
        data["last_payment"] = extract_numeric(latest_payment.get("amount"))
        data["last_payment_data"] = dict(latest_payment)
    elif bills and bills[0].get("payments"):
        payments = bills[0]["payments"]
        if payments:
            last_payment = payments[0]
            data["last_payment"] = extract_numeric(last_payment.get("amount"))
            data["last_payment_data"] = dict(last_payment)

    data["due_date"] = details.get("due_date")
    data["kwh_cost"] = details.get("kwh_cost")
    data["last_bill_kwh"] = details.get("kwh_used")

    forecast = meter.get("forecast") or {}
    reading = meter.get("reading") or {}
    usage_cost = meter.get("usage_to_date_cost")
    if usage_cost is None:
        usage_cost = meter.get("cost")
    data["current_usage_cost"] = usage_cost
    data["current_meter_usage"] = reading.get("value") if isinstance(reading, dict) else None
    if forecast:
        data["billing_start_date"] = forecast.get("start_date")
        data["billing_end_date"] = forecast.get("end_date")
        data["current_cycle_usage"] = forecast.get("usage_to_date")
        data["forecasted_usage"] = forecast.get("forecasted_usage")

    summary = payee_summary
    if summary is None and bills:
        summary = _lookup_summary(ledger.get("payee_summaries") or {}, bills[0].get("id"))
        if summary and "payees" not in summary:
            # Frontend format uses payee_summaries list.
            converted = dict(summary)
            converted["payees"] = converted.get("payee_summaries") or []
            summary = converted
    if summary is None and isinstance(ledger.get("payee_summaries"), list):
        raw_list = ledger.get("payee_summaries") or []
        summary = raw_list[0] if raw_list else None

    payee_attrs = build_payee_summary_attributes(summary, today=today)
    data["payee_summary"] = payee_attrs.get("bill_balance", 0.0)
    data["payee_summary_data"] = payee_attrs
    return data
