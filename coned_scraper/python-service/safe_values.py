"""Coercions that stop ledger and history handlers from crashing on bad payloads."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional


def safe_float(val: Any) -> Optional[float]:
    """Float conversion that returns None instead of raising."""
    if val is None or isinstance(val, bool):
        return None
    try:
        number = float(val)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def aware_datetime(value: Optional[datetime]) -> datetime:
    """Sort key that never mixes naive and aware datetimes.

    Missing values sort as the earliest UTC instant. Naive values are treated
    as UTC, matching parse_date().
    """
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def as_charge_map(value: Any) -> dict:
    """Bill supply/delivery JSON is normally a dict, but older rows are strings."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def charge_total(value: Any) -> float:
    total = safe_float(as_charge_map(value).get("total"))
    return 0.0 if total is None else total


def is_db_connection_error(exc: BaseException) -> bool:
    """True when retrying after a reconnect can succeed. Not for bad data."""
    text = f"{type(exc).__name__} {exc}".lower()
    needles = (
        "can't reach database",
        "cannot reach database",
        "server closed the connection",
        "connection refused",
        "connection reset",
        "connection closed",
        "connectiondoesnotexist",
        "not connected",
        "engine is not yet connected",
        "query engine",
        "broken pipe",
        "connection timed out",
        "timeout expired",
        "could not connect",
        "too many clients",
        "remaining connection slots",
        "environment variable not found",
        "database_url",
    )
    return any(needle in text for needle in needles)
