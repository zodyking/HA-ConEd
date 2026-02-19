"""
Scheduled bill summary TTS. Runs between configured hours on selected days.
Builds message from bill, balance, and HA sensors.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

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
    "sensor_avg_daily": "",
    "sensor_estimate_min": "",
    "sensor_estimate_max": "",
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
    if bill_amt <= 350:
        return ""
    return (
        " Your bill was higher than expected. Consider reducing usage: "
        "turn off heaters and air conditioning when leaving home for extended periods."
    )


def _estimate_message(est_min: float, est_max: float) -> str:
    if est_min <= 350 and est_max <= 350:
        return ""
    return (
        " Current usage patterns suggest your bill could be high. "
        "You can still reduce your electric use this cycle to lower the final bill."
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
        config.get("sensor_avg_daily"),
        config.get("sensor_estimate_min"),
        config.get("sensor_estimate_max"),
    ]
    sensor_ids = [s for s in sensor_ids if s and isinstance(s, str)]
    sensor_vals = await _get_ha_sensor_values(sensor_ids) if sensor_ids else {}

    avg_daily = "unknown"
    if config.get("sensor_avg_daily"):
        avg_daily = sensor_vals.get(config["sensor_avg_daily"], "unknown")

    est_min_val = _parse_amount(sensor_vals.get(config.get("sensor_estimate_min", ""), "0"))
    est_max_val = _parse_amount(sensor_vals.get(config.get("sensor_estimate_max", ""), "0"))

    est_str = f"{_format_currency(est_min_val)} to {_format_currency(est_max_val)}"
    if not config.get("sensor_estimate_min") and not config.get("sensor_estimate_max"):
        est_str = "not available"

    # Build message parts
    parts = [
        f"Your latest Con Edison bill was {bill_str} and your current account balance is {balance_str}."
    ]
    parts.append(_bill_message(bill_amt))
    parts.append(
        f" Your average daily power consumption is {avg_daily}. "
        f"Based on current usage patterns, we estimate your bill will be {est_str} "
        "by the end of the billing cycle."
    )
    parts.append(_estimate_message(est_min_val, est_max_val))

    msg = "".join(parts).strip()
    return f"{prefix} {msg}".strip()


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

    now = datetime.now(timezone.utc)
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
    """Start the bill summary check loop (runs every minute)."""
    global _bill_summary_task

    async def _loop():
        while True:
            try:
                await _maybe_trigger_bill_summary()
            except Exception as e:
                logger.exception("Bill summary scheduler error")
            await asyncio.sleep(60)

    _bill_summary_task = asyncio.create_task(_loop())
    logger.info("TTS bill summary scheduler started")
