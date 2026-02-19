"""
Scheduled bill summary TTS. Runs between configured hours on selected days.
Builds message from bill, balance, and HA sensors.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

from data_config import DATA_DIR
TTS_BILL_SUMMARY_CONFIG_FILE = DATA_DIR / "tts_bill_summary_config.json"

DEFAULT_BILL_SUMMARY_CONFIG = {
    "enabled": False,
    "days_of_week": [0, 1, 2, 3, 4, 5, 6],  # 0=Monday in Python
    "start_hour": 8,
    "end_hour": 10,
    "frequency_hours": 1,  # Play every N hours
    "minute_of_hour": 0,   # Play at minute X (0-59)
    "sensor_current_usage": "",   # "You used X so far this cycle" (kWh)
    "sensor_avg_daily": "",       # kWh per day
    "sensor_estimate_min": "",    # kWh - will convert to $ via kwh_cost
    "sensor_estimate_max": "",    # kWh - will convert to $ via kwh_cost
    "sensor_kwh_cost": "",        # $ per kWh (helper, e.g. input_number)
    "timezone_offset_hours": 0,  # Local = UTC + this (e.g. -5 for EST)
    "last_played_slot": None,  # YYYY-MM-DD-HH to avoid replay same slot
}


def load_bill_summary_config() -> dict:
    if not TTS_BILL_SUMMARY_CONFIG_FILE.exists():
        return DEFAULT_BILL_SUMMARY_CONFIG.copy()
    try:
        data = json.loads(TTS_BILL_SUMMARY_CONFIG_FILE.read_text())
        out = DEFAULT_BILL_SUMMARY_CONFIG.copy()
        out.update(data)
        return out
    except Exception as e:
        logger.warning(f"Failed to load bill summary config: {e}")
        return DEFAULT_BILL_SUMMARY_CONFIG.copy()


def save_bill_summary_config(config: dict):
    TTS_BILL_SUMMARY_CONFIG_FILE.write_text(json.dumps(config))


def _parse_amount(val) -> float:
    from database import parse_amount
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    return parse_amount(str(val)) or 0.0


def _parse_float(val) -> Optional[float]:
    """Parse string to float for kWh-style values. Returns None if not numeric."""
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip()
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


def _format_kwh(val) -> str:
    """Format value as 'X kilowatt hours' if numeric, else return as-is."""
    n = _parse_float(val)
    if n is not None:
        s = f"{n:.1f}" if n != int(n) else str(int(n))
        return f"{s} kilowatt hours"
    return str(val) if val else "unknown"


async def _get_ha_sensor_values(entity_ids: list) -> Dict[str, str]:
    """Fetch HA entity states. Returns {entity_id: state}."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token or not entity_ids:
        return {}
    ids = [e.strip() for e in entity_ids if e and isinstance(e, str)]
    if not ids:
        return {}
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://supervisor/core/api/states",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                by_id = {
                    s["entity_id"]: s.get("state", "unknown")
                    for s in (data or [])
                    if isinstance(s, dict) and "entity_id" in s
                }
                return {e: by_id.get(e, "unknown") for e in ids}
    except Exception as e:
        logger.debug(f"Could not get HA sensor values: {e}")
        return {}


def _format_currency(val: float) -> str:
    return f"${val:,.2f}" if val is not None else "$0.00"


def _bill_message(bill_amt: float) -> str:
    """Dynamic feedback based on bill amount: 0-150 excellent, 150-250 good, 250-350 moderate, 350+ high."""
    if bill_amt <= 0:
        return ""
    if bill_amt <= 150:
        return " Your bill is in an excellent range."
    if bill_amt <= 250:
        return " Your bill is in a good range."
    if bill_amt <= 350:
        return " Your bill is on the higher side. Consider small reductions in usage."
    return (
        " Your bill was much higher than expected. Reduce usage: "
        "turn off heaters and air conditioning when leaving home, and cut back on high-use appliances."
    )


def _estimate_message(est_min: float, est_max: float) -> str:
    """Dynamic feedback based on projected bill estimates."""
    est_mid = (est_min + est_max) / 2 if (est_min or est_max) else 0
    if est_mid <= 0:
        return ""
    if est_mid <= 200:
        return " Your projected bill looks good."
    if est_mid <= 300:
        return " Your projected bill is moderate. Small cuts can lower the final amount."
    if est_mid <= 400:
        return (
            " Your projected bill is running high. "
            "Reduce electric use now to bring the final bill down."
        )
    return (
        " Your projected bill is way too high. "
        "Turn off heaters and AC when away, avoid peak-hour usage, and cut non-essential loads."
    )


def _daily_usage_message(avg_daily: float) -> str:
    """0-14 really efficient, 15-22 good, 22-30 too high, 30+ way too high."""
    if avg_daily <= 0:
        return ""
    if avg_daily < 15:
        return " Your daily usage is really efficient."
    if avg_daily <= 22:
        return " Your daily usage is in a good range."
    if avg_daily <= 30:
        return (
            " Your daily usage is running too high. "
            "Consider reducing appliance use during peak hours."
        )
    return (
        " Your daily usage is way too high. "
        "Turn off heaters and AC when away, and reduce appliance use."
    )


def _current_usage_message(current_kwh: float, typical_cycle: float = 300) -> str:
    """Feedback on cycle-to-date usage. typical_cycle ~mid-cycle expectation for context."""
    if current_kwh <= 0:
        return ""
    if current_kwh <= 100:
        return " You're off to an efficient start this cycle."
    if current_kwh <= 200:
        return " Your cycle usage is on track."
    if current_kwh <= 350:
        return " Your cycle usage is running high. Try to reduce going forward."
    return (
        " Your cycle usage is very high. "
        "Focus on reducing consumption for the rest of the billing period."
    )


async def build_bill_summary_message(bill_summary_config: dict, tts_config: dict) -> Optional[str]:
    """
    Build the scheduled bill summary TTS message.
    Uses: latest bill amount, account balance, HA sensors for avg daily + estimates.
    """
    prefix = (tts_config.get("prefix") or "Message from Con Edison.").strip()
    prefix = f"{prefix} " if not prefix.endswith(".") and not prefix.endswith(" ") else prefix

    # Latest bill
    from database import get_all_bills, get_current_balance
    bills = get_all_bills(limit=1)
    bill_amt = 0.0
    bill_str = "$0"
    if bills:
        b = bills[0]
        bill_amt = _parse_amount(b.get("bill_total") or b.get("amount_numeric"))
        bill_str = _format_currency(bill_amt)

    # Account balance
    bal_row = get_current_balance()
    balance_str = "$0"
    if bal_row and bal_row.get("balance"):
        balance_str = str(bal_row["balance"])

    # HA sensors
    config = bill_summary_config
    sensor_ids = [
        config.get("sensor_current_usage"),
        config.get("sensor_avg_daily"),
        config.get("sensor_estimate_min"),
        config.get("sensor_estimate_max"),
        config.get("sensor_kwh_cost"),
    ]
    sensor_ids = [s for s in sensor_ids if s and isinstance(s, str)]
    sensor_vals = await _get_ha_sensor_values(sensor_ids) if sensor_ids else {}

    current_usage_raw = "unknown"
    if config.get("sensor_current_usage"):
        current_usage_raw = sensor_vals.get(config["sensor_current_usage"], "unknown")
    current_usage = _format_kwh(current_usage_raw)

    avg_daily_raw = "unknown"
    if config.get("sensor_avg_daily"):
        avg_daily_raw = sensor_vals.get(config["sensor_avg_daily"], "unknown")
    avg_daily = _format_kwh(avg_daily_raw)

    # Estimates: kWh from sensors, convert to $ via kwh_cost
    est_min_kwh = _parse_amount(sensor_vals.get(config.get("sensor_estimate_min", ""), "0"))
    est_max_kwh = _parse_amount(sensor_vals.get(config.get("sensor_estimate_max", ""), "0"))
    kwh_cost_raw = sensor_vals.get(config.get("sensor_kwh_cost", ""), "0") if config.get("sensor_kwh_cost") else "0"
    kwh_cost = _parse_amount(str(kwh_cost_raw)) if kwh_cost_raw else 0.0

    if kwh_cost and kwh_cost > 0 and (config.get("sensor_estimate_min") or config.get("sensor_estimate_max")):
        est_min_val = est_min_kwh * kwh_cost
        est_max_val = est_max_kwh * kwh_cost
        est_str = f"{_format_currency(est_min_val)} to {_format_currency(est_max_val)}"
    else:
        est_min_val = 0.0
        est_max_val = 0.0
        if config.get("sensor_estimate_min") or config.get("sensor_estimate_max"):
            est_str = "not available (add kWh cost sensor to convert to dollars)"
        else:
            est_str = "not available"

    avg_daily_num = _parse_float(avg_daily_raw) or 0.0
    current_usage_num = _parse_float(current_usage_raw) or 0.0

    # Build message parts: report each value, then its commentary, before moving to the next topic
    parts = [
        f"Your latest Con Edison bill was {bill_str} and your current account balance is {balance_str}."
    ]
    parts.append(_bill_message(bill_amt))

    if config.get("sensor_current_usage"):
        parts.append(f" You have used {current_usage} so far this billing cycle.")
        parts.append(_current_usage_message(current_usage_num))

    parts.append(f" Your average daily power consumption is {avg_daily}.")
    parts.append(_daily_usage_message(avg_daily_num))

    parts.append(
        f" Based on current usage patterns, we estimate your bill will be {est_str} "
        "by the end of the billing cycle."
    )
    parts.append(_estimate_message(est_min_val, est_max_val) if (est_min_val or est_max_val) else "")

    msg = "".join(parts).strip()
    return f"{prefix} {msg}".strip()


_cached_ha_timezone: Optional[str] = None
_cached_ha_timezone_at: Optional[datetime] = None
_CACHE_TTL_SECONDS = 3600  # 1 hour


async def _get_ha_timezone() -> Optional[str]:
    """Fetch timezone from Home Assistant /api/config. Cached for 1 hour."""
    global _cached_ha_timezone, _cached_ha_timezone_at
    now = datetime.now(timezone.utc)
    if _cached_ha_timezone is not None and _cached_ha_timezone_at is not None:
        if (now - _cached_ha_timezone_at).total_seconds() < _CACHE_TTL_SECONDS:
            return _cached_ha_timezone
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://supervisor/core/api/config",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                tz = (data.get("time_zone") or "").strip()
                if tz:
                    # Validate it's a known zone
                    try:
                        ZoneInfo(tz)
                        _cached_ha_timezone = tz
                        _cached_ha_timezone_at = now
                        return tz
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Could not get HA timezone: {e}")
    return None


async def _get_local_now(cfg: dict):
    """Get current time in user's local zone. Uses HA timezone when available, else timezone_offset_hours."""
    now_utc = datetime.now(timezone.utc)
    tz_str = await _get_ha_timezone()
    if tz_str:
        return now_utc.astimezone(ZoneInfo(tz_str))
    offset = int(cfg.get("timezone_offset_hours", 0))
    return now_utc + timedelta(hours=offset)


async def _maybe_trigger_bill_summary():
    """Check if we're in the time window and day, then queue bill summary TTS."""
    cfg = load_bill_summary_config()
    if not cfg.get("enabled"):
        return

    from main import load_tts_config
    tts_cfg = load_tts_config()
    if not tts_cfg.get("enabled"):
        return
    media_players = tts_cfg.get("media_players") or []
    media_players = [p for p in media_players if isinstance(p, dict) and (p.get("entity_id") or "").strip()]
    if not media_players:
        return
    tts_engine = (tts_cfg.get("tts_engine") or "").strip()
    if not tts_engine:
        return

    now = await _get_local_now(cfg)
    # Python: weekday() 0=Monday, 6=Sunday
    day = now.weekday()
    hour = now.hour
    minute = now.minute
    start_h = int(cfg.get("start_hour", 8))
    end_h = int(cfg.get("end_hour", 10))
    freq_h = max(1, int(cfg.get("frequency_hours", 1)))
    min_of_hour = max(0, min(59, int(cfg.get("minute_of_hour", 0))))
    days = cfg.get("days_of_week") or [0, 1, 2, 3, 4, 5, 6]

    if day not in days:
        return

    # Valid slot hours: start, start+freq, start+2*freq, ... < end
    slot_hours = []
    h = start_h
    while h < end_h:
        slot_hours.append(h)
        h += freq_h
    if hour not in slot_hours:
        return
    if minute < min_of_hour:
        return

    slot_str = now.strftime("%Y-%m-%d-%H")
    if cfg.get("last_played_slot") == slot_str:
        return

    try:
        msg = await build_bill_summary_message(cfg, tts_cfg)
        if not msg:
            return

        from tts_queue import enqueue_tts
        await enqueue_tts(
            source="scheduled_bill_summary",
            message=msg,
            media_players=media_players,
            tts_engine=tts_engine,
            cache=tts_cfg.get("cache", True),
            wait_for_idle=tts_cfg.get("wait_for_idle", True),
        )
        cfg["last_played_slot"] = slot_str
        save_bill_summary_config(cfg)
        from main import add_log
        add_log("info", "Queued scheduled bill summary TTS")
    except Exception as e:
        logger.exception("Bill summary TTS failed")
        from main import add_log
        add_log("error", f"Bill summary TTS error: {e}")


_bill_summary_task = None


def start_bill_summary_scheduler():
    """Start the bill summary check loop. Polls every 30s for accurate trigger timing."""
    global _bill_summary_task

    async def _loop():
        while True:
            try:
                await _maybe_trigger_bill_summary()
            except Exception as e:
                logger.exception("Bill summary scheduler error")
            await asyncio.sleep(30)

    _bill_summary_task = asyncio.create_task(_loop())
    logger.info("TTS bill summary scheduler started")
