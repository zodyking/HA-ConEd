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
    "sensor_current_usage": "",
    "sensor_avg_daily": "",
    "sensor_estimate_min": "",
    "sensor_estimate_max": "",
    "sensor_kwh_cost": "",
    "last_played_slot": None,
    # Thresholds for message commentary (configurable)
    "threshold_bill_good": 150,
    "threshold_bill_moderate": 250,
    "threshold_bill_high": 350,
    "threshold_estimate_good": 200,
    "threshold_estimate_moderate": 300,
    "threshold_estimate_high": 400,
    "threshold_daily_kwh_good": 15,
    "threshold_daily_kwh_high": 22,
    "threshold_daily_kwh_very_high": 30,
    "threshold_cycle_kwh_efficient": 100,
    "threshold_cycle_kwh_high": 200,
    "threshold_cycle_kwh_very_high": 350,
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


def _bill_message(bill_amt: float, good: float, moderate: float, high: float) -> str:
    """Feedback based on configurable bill thresholds. Full sentences for TTS clarity."""
    if bill_amt <= 0:
        return ""
    if bill_amt <= good:
        return " Your bill is in a good range."
    if bill_amt <= moderate:
        return " Your bill is moderate."
    if bill_amt <= high:
        return " Your bill is high. Consider reducing usage."
    return (
        " Your bill is very high. "
        "Try cutting back on heaters, air conditioning, and appliances when you're away."
    )


def _estimate_message(est_min: float, est_max: float, good: float, moderate: float, high: float) -> str:
    """Feedback based on configurable estimate thresholds. Full sentences for TTS."""
    est_mid = (est_min + est_max) / 2 if (est_min or est_max) else 0
    if est_mid <= 0:
        return ""
    if est_mid <= good:
        return " Your projected bill looks good."
    if est_mid <= moderate:
        return " Your projected bill is moderate."
    if est_mid <= high:
        return " Your projected bill is high. Reduce use to bring it down."
    return (
        " Your projected bill is very high. "
        "Cut back on electric use now to lower the final amount."
    )


def _daily_usage_message(avg_daily: float, good: float, high: float, very_high: float) -> str:
    """Feedback based on configurable daily kWh thresholds. Full sentences for TTS."""
    if avg_daily <= 0:
        return ""
    if avg_daily < good:
        return " Your daily usage is efficient."
    if avg_daily <= high:
        return " Your daily usage is okay."
    if avg_daily <= very_high:
        return " Your daily usage is running high."
    return " Your daily usage is very high."


def _current_usage_message(
    current_kwh: float, efficient: float, high: float, very_high: float
) -> str:
    """Feedback based on configurable cycle kWh thresholds. Full sentences for TTS."""
    if current_kwh <= 0:
        return ""
    if current_kwh <= efficient:
        return " You're off to an efficient start this cycle."
    if current_kwh <= high:
        return " Your cycle usage is on track."
    if current_kwh <= very_high:
        return " Your cycle usage is running high."
    return " Your cycle usage is very high."


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

    # Thresholds from config
    t = config
    bill_good = float(t.get("threshold_bill_good", 150))
    bill_mod = float(t.get("threshold_bill_moderate", 250))
    bill_high = float(t.get("threshold_bill_high", 350))
    est_good = float(t.get("threshold_estimate_good", 200))
    est_mod = float(t.get("threshold_estimate_moderate", 300))
    est_high = float(t.get("threshold_estimate_high", 400))
    daily_good = float(t.get("threshold_daily_kwh_good", 15))
    daily_high = float(t.get("threshold_daily_kwh_high", 22))
    daily_vhigh = float(t.get("threshold_daily_kwh_very_high", 30))
    cycle_eff = float(t.get("threshold_cycle_kwh_efficient", 100))
    cycle_high = float(t.get("threshold_cycle_kwh_high", 200))
    cycle_vhigh = float(t.get("threshold_cycle_kwh_very_high", 350))

    # Build message for TTS: complete sentences, clear structure for listening
    parts = [
        f"Your latest bill was {bill_str}. Your current balance is {balance_str}.",
    ]
    parts.append(_bill_message(bill_amt, bill_good, bill_mod, bill_high))

    if config.get("sensor_current_usage"):
        parts.append(f" You've used {current_usage} so far this billing cycle.")
        parts.append(_current_usage_message(current_usage_num, cycle_eff, cycle_high, cycle_vhigh))

    parts.append(f" Your average is {avg_daily} per day.")
    parts.append(_daily_usage_message(avg_daily_num, daily_good, daily_high, daily_vhigh))

    parts.append(
        f" Based on current usage, we estimate your bill will be {est_str} by the end of the billing cycle."
    )
    if est_min_val or est_max_val:
        parts.append(_estimate_message(est_min_val, est_max_val, est_good, est_mod, est_high))

    msg = " ".join(p.strip() for p in parts if p).strip()
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


async def _get_local_now(_cfg: dict):
    """Get current time in user's local zone. Uses HA timezone only (no fallback)."""
    now_utc = datetime.now(timezone.utc)
    tz_str = await _get_ha_timezone()
    if tz_str:
        return now_utc.astimezone(ZoneInfo(tz_str))
    return now_utc  # Fallback: UTC when HA timezone unavailable


def _compute_next_slot(now: datetime, cfg: dict) -> Optional[datetime]:
    """Compute next valid run time. Returns None if no valid slot in next 8 days."""
    start_h = int(cfg.get("start_hour", 8))
    end_h = int(cfg.get("end_hour", 10))
    freq_h = max(1, int(cfg.get("frequency_hours", 1)))
    min_of_hour = max(0, min(59, int(cfg.get("minute_of_hour", 0))))
    days_set = set(cfg.get("days_of_week") or [0, 1, 2, 3, 4, 5, 6])
    slot_hours = list(range(start_h, end_h, freq_h))
    if not slot_hours:
        return None
    for day_offset in range(8):
        d = now.date() + timedelta(days=day_offset)
        if d.weekday() not in days_set:
            continue
        for sh in slot_hours:
            slot = datetime(d.year, d.month, d.day, sh, min_of_hour, 0, 0, tzinfo=now.tzinfo)
            if slot > now:
                return slot
    return None


async def _maybe_trigger_bill_summary() -> bool:
    """Check if we're in the time window and day, then queue bill summary TTS. Returns True if triggered."""
    cfg = load_bill_summary_config()
    if not cfg.get("enabled"):
        return False

    from main import load_tts_config
    tts_cfg = load_tts_config()
    if not tts_cfg.get("enabled"):
        return False
    media_players = tts_cfg.get("media_players") or []
    media_players = [p for p in media_players if isinstance(p, dict) and (p.get("entity_id") or "").strip()]
    if not media_players:
        return False
    tts_engine = (tts_cfg.get("tts_engine") or "").strip()
    if not tts_engine:
        return False

    now = await _get_local_now(cfg)
    day = now.weekday()
    hour = now.hour
    minute = now.minute
    start_h = int(cfg.get("start_hour", 8))
    end_h = int(cfg.get("end_hour", 10))
    freq_h = max(1, int(cfg.get("frequency_hours", 1)))
    min_of_hour = max(0, min(59, int(cfg.get("minute_of_hour", 0))))
    days = cfg.get("days_of_week") or [0, 1, 2, 3, 4, 5, 6]

    if day not in days:
        return False

    slot_hours = []
    h = start_h
    while h < end_h:
        slot_hours.append(h)
        h += freq_h
    if hour not in slot_hours:
        return False
    if minute < min_of_hour:
        return False

    slot_str = now.strftime("%Y-%m-%d-%H")
    if cfg.get("last_played_slot") == slot_str:
        return False

    try:
        msg = await build_bill_summary_message(cfg, tts_cfg)
        if not msg:
            return False

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
        return True
    except Exception as e:
        logger.exception("Bill summary TTS failed")
        from main import add_log
        add_log("error", f"Bill summary TTS error: {e}")
        return False


_bill_summary_task = None


def start_bill_summary_scheduler():
    """Start the bill summary scheduler. Sleeps until next slot for reliable timing (like cron)."""
    global _bill_summary_task

    async def _loop():
        while True:
            try:
                cfg = load_bill_summary_config()
                if not cfg.get("enabled"):
                    await asyncio.sleep(60)
                    continue
                now = await _get_local_now(cfg)
                next_slot = _compute_next_slot(now, cfg)
                if next_slot:
                    wait_secs = (next_slot - now).total_seconds()
                    # Wake 20s before slot, then poll every 5s until we pass it
                    if wait_secs > 25:
                        await asyncio.sleep(min(55, wait_secs - 20))
                        continue
                    if wait_secs > 5:
                        await asyncio.sleep(5)
                        continue
                triggered = await _maybe_trigger_bill_summary()
                # After trigger, wait at least 60s to avoid double-check
                await asyncio.sleep(60 if triggered else 30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Bill summary scheduler error")
                await asyncio.sleep(60)

    _bill_summary_task = asyncio.create_task(_loop())
    logger.info("TTS bill summary scheduler started (cron-style)")
