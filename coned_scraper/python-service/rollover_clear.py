"""Undoable rollover-balance clear marker.

One active marker: starting at month YYYY-MM, the carried payee balance going
into that month is treated as zero. Later months carry forward from that
cleared baseline. Removing the marker restores the previous chain.

This module is the seam around the payee rollover formula. It does not
recompute how an underpayment becomes the next bill's carry.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

ROLLOVER_CLEAR_SETTING_KEY = "rollover_clear"

_MONTH_LABELS = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_ISO_MONTH = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?(?:[T\s].*)?$")
_US_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def normalize_clear_month(value: Any) -> Optional[str]:
    """Return YYYY-MM, or None when the value is empty or not a real month."""
    if value is None:
        return None
    if isinstance(value, datetime):
        year, month = value.year, value.month
    elif isinstance(value, date):
        year, month = value.year, value.month
    elif isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"null", "none"}:
            return None
        iso = _ISO_MONTH.match(text)
        if iso:
            year, month = int(iso.group(1)), int(iso.group(2))
        else:
            us = _US_DATE.match(text)
            if not us:
                return None
            month, year = int(us.group(1)), int(us.group(3))
    else:
        return None
    if month < 1 or month > 12 or year < 1900 or year > 9999:
        return None
    return f"{year:04d}-{month:02d}"


def format_clear_month_label(month: Optional[str]) -> Optional[str]:
    """March 2024 style label for a YYYY-MM marker."""
    normalized = normalize_clear_month(month)
    if not normalized:
        return None
    year, mon = normalized.split("-")
    return f"{_MONTH_LABELS[int(mon)]} {year}"


def marker_from_setting(value: Any) -> Optional[str]:
    """Read the stored app-setting payload. A null month means the clear was undone."""
    if isinstance(value, dict):
        return normalize_clear_month(value.get("month"))
    if isinstance(value, str):
        return normalize_clear_month(value)
    return None


def bill_month_key(billing_period_start: Any = None, bill_cycle_date: Any = None) -> Optional[str]:
    """Month a bill belongs to for the clear boundary.

    Billing-period start is the month the statement period begins. The bill
    cycle date is the fallback when period details are missing.
    """
    return normalize_clear_month(billing_period_start) or normalize_clear_month(bill_cycle_date)


def apply_rollover_clear(balance: float, month: Optional[str], clear_marker: Optional[str]) -> float:
    """Zero the carried balance when this bill's month is on or after the marker.

    Callers that walk bills oldest-first must stop passing the marker after the
    boundary bill. Otherwise every later month would also be forced to zero
    and could not carry forward from the cleared baseline.
    """
    try:
        carried = float(balance or 0.0)
    except (TypeError, ValueError):
        carried = 0.0
    marker = normalize_clear_month(clear_marker)
    bill_month = normalize_clear_month(month)
    if marker and bill_month and bill_month >= marker:
        return 0.0
    return carried


def apply_rollover_clear_at_bill(
    rollover_by_user: Dict[Any, float],
    month: Optional[str],
    clear_marker: Optional[str],
) -> Tuple[Dict[Any, float], Optional[str]]:
    """Apply the clear once, at the first bill on or after the marker month.

    Returns the balances to use as this bill's incoming rollover, and the
    marker to pass to later bills (None after the boundary is consumed).
    """
    marker = normalize_clear_month(clear_marker)
    if not marker:
        return rollover_by_user, None
    bill_month = normalize_clear_month(month)
    if not bill_month or bill_month < marker:
        return rollover_by_user, marker
    cleared = {
        user_id: apply_rollover_clear(balance, bill_month, marker)
        for user_id, balance in rollover_by_user.items()
    }
    return cleared, None
