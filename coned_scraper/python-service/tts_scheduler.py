"""
TTS Scheduler for Con Edison Addon.
Handles scheduled TTS announcements including:
- Scheduled bill summary announcements (daily/weekly)
- Time-based triggers with day filtering
- Event-triggered TTS for new bills and payments
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data") if Path("/data").exists() else Path(__file__).parent / "data"
TTS_SCHEDULE_FILE = DATA_DIR / "tts_schedule.json"
TTS_CONFIG_FILE = DATA_DIR / "tts_config.json"

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


async def build_scheduled_bill_summary_message(
    ledger: Dict[str, Any],
    schedule_config: Dict[str, Any],
    tts_config: Dict[str, Any],
) -> str:
    """
    Build the same scheduled bill-summary string as the TTS scheduler (including pending-new-bill branch).
    Used by TTSScheduler and /api/tts/preview-message.
    """
    import db
    import aiohttp
    import os
    from meter_service import get_meter_service

    template = schedule_config.get("message_template", "")
    current_usage_sensor = schedule_config.get("current_usage_sensor", "")
    future_usage_sensor = schedule_config.get("future_usage_sensor", "")
    prefix = tts_config.get("prefix", "Message from Con Edison.")

    if not template:
        template = (
            "{prefix} Your current balance is {balance}. Your last bill was {latest_bill_amount}, "
            "using {last_bill_kwh}, due {due_date}."
        )

    bills = ledger.get("bills", [])
    latest_bill = bills[0] if bills else {}
    latest_bill_id = latest_bill.get("id")

    bill_details = await db.get_bill_details(latest_bill_id) if latest_bill_id else None

    balance = ledger.get("account_balance") or ledger.get("total_balance", "")
    if isinstance(balance, (int, float)):
        balance = f"${balance:.2f}"

    def format_date_for_tts(date_str: str) -> str:
        if not date_str:
            return ""
        try:
            from dateutil import parser as date_parser

            dt = date_parser.parse(date_str)
            return dt.strftime("%B %d").replace(" 0", " ")
        except Exception:
            import re

            match = re.search(r"(\w{3,9})\s+(\d{1,2})", date_str)
            if match:
                return f"{match.group(1)} {int(match.group(2))}"
            return date_str

    bill_amount = latest_bill.get("bill_total", "") or latest_bill.get("amount", "")

    due_date_raw = latest_bill.get("due_date", "") or ""
    due_date = format_date_for_tts(due_date_raw)

    last_bill_kwh = ""
    kwh_cost = None

    if bill_details:
        kwh_val = bill_details.get("kwh_used")
        if kwh_val:
            last_bill_kwh = f"{int(round(kwh_val))} kWh"
        kwh_cost = bill_details.get("kwh_cost")
        if not due_date:
            due_date = format_date_for_tts(bill_details.get("due_date", "") or "")

    current_usage_kwh = ""
    current_usage_cost = ""
    projected_usage_kwh = ""
    projected_usage_cost = ""

    # Match GET /api/meter-reading: only use forecast when meter service is enabled
    forecast = None
    meter_service = get_meter_service()
    if meter_service.is_enabled():
        try:
            forecast = await db.get_meter_forecast_db()
        except Exception as e:
            logger.warning(f"Failed to load cached meter forecast for TTS: {e}")

    if forecast:
        try:
            usage_to_date = forecast.get("usage_to_date")
            if usage_to_date is not None:
                current_usage_kwh = f"{int(round(usage_to_date))} kWh"
                if kwh_cost:
                    cost_val = usage_to_date * kwh_cost
                    current_usage_cost = f"${cost_val:.2f}"

            forecasted = forecast.get("forecasted_usage")
            if forecasted is not None:
                projected_usage_kwh = f"{int(round(forecasted))} kWh"
                if kwh_cost:
                    cost_val = forecasted * kwh_cost
                    projected_usage_cost = f"${cost_val:.2f}"
        except Exception as e:
            logger.warning(f"Failed to apply meter forecast to TTS message: {e}")

    elif current_usage_sensor or future_usage_sensor:
        token = os.environ.get("SUPERVISOR_TOKEN")
        if token:
            async with aiohttp.ClientSession() as session:
                if current_usage_sensor and current_usage_sensor.strip():
                    try:
                        async with session.get(
                            f"http://supervisor/core/api/states/{current_usage_sensor.strip()}",
                            headers={"Authorization": f"Bearer {token}"},
                        ) as resp:
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        current_usage_kwh = f"{int(round(kwh_value))} kWh"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            current_usage_cost = f"${cost_value:.2f}"
                                    except ValueError:
                                        current_usage_kwh = f"{sensor_state} kWh"
                    except Exception as e:
                        logger.warning(f"Failed to fetch current usage sensor: {e}")

                if future_usage_sensor and future_usage_sensor.strip():
                    try:
                        async with session.get(
                            f"http://supervisor/core/api/states/{future_usage_sensor.strip()}",
                            headers={"Authorization": f"Bearer {token}"},
                        ) as resp:
                            if resp.status == 200:
                                state_data = await resp.json()
                                sensor_state = state_data.get("state", "")
                                if sensor_state and sensor_state not in ("unknown", "unavailable"):
                                    try:
                                        kwh_value = float(sensor_state)
                                        projected_usage_kwh = f"{int(round(kwh_value))} kWh"
                                        if kwh_cost:
                                            cost_value = kwh_value * kwh_cost
                                            projected_usage_cost = f"${cost_value:.2f}"
                                    except ValueError:
                                        projected_usage_kwh = f"{sensor_state} kWh"
                    except Exception as e:
                        logger.warning(f"Failed to fetch future usage sensor: {e}")

    placeholders = {
        "prefix": prefix,
        "balance": balance or "N/A",
        "latest_bill_amount": bill_amount or "N/A",
        "due_date": due_date or "N/A",
        "last_bill_kwh": last_bill_kwh or "N/A",
        "current_usage_kwh": current_usage_kwh or "N/A",
        "current_usage_cost": current_usage_cost or "N/A",
        "projected_usage_kwh": projected_usage_kwh or "N/A",
        "projected_usage_cost": projected_usage_cost or "N/A",
    }

    pending = ledger.get("pending_new_bill") or {}
    if pending.get("active"):
        pending_lead = (
            "{prefix} A new bill is being generated; it typically takes one to three days to post. "
            "Your account balance already reflects the new bill plus any unpaid balances. "
        )
        message = pending_lead
        for key, value in placeholders.items():
            message = message.replace(f"{{{key}}}", str(value) if value else "N/A")
        usage_suffix = (
            "So far this billing period, usage is about {current_usage_kwh} ({current_usage_cost}). "
            "Projected by cycle end: about {projected_usage_kwh} ({projected_usage_cost})."
        )
        for key, value in placeholders.items():
            usage_suffix = usage_suffix.replace(f"{{{key}}}", str(value) if value else "N/A")
        message += " " + usage_suffix
    else:
        message = template
        for key, value in placeholders.items():
            message = message.replace(f"{{{key}}}", str(value) if value else "N/A")

    return message


class TTSScheduler:
    """Manages scheduled TTS announcements."""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_triggered: Dict[str, datetime] = {}
    
    async def load_schedule_config(self) -> Dict[str, Any]:
        """Load TTS schedule configuration from database (persists across reinstalls)."""
        import db
        
        defaults = {
            "enabled": False,
            "hour_pattern": 3,  # Announce every N hours
            "minute_offset": 0,  # Minute within hour (e.g., :00, :30)
            "start_time": "08:00",  # Active hours start
            "end_time": "21:00",  # Active hours end
            "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
            "message_template": "{prefix} Your current bill is {latest_bill_amount}, using {last_bill_kwh}, due {due_date}. Your account balance is {balance}. Current usage: {current_usage_kwh} at {current_usage_cost}. Projected usage: {projected_usage_kwh} at {projected_usage_cost}.",
            "current_usage_sensor": "",  # HA sensor entity for current kWh usage
            "future_usage_sensor": "",  # HA sensor entity for projected kWh usage
            "schedule_times": [],  # Legacy: List of {"time": "08:00", "days": ["mon", "tue", ...]}
            "schedule_type": "daily",  # Legacy
            "updated_at": None
        }
        
        # Try database first
        data = await db.get_tts_schedule_db()
        
        # Migrate from JSON file if database is empty but file exists
        if data is None and TTS_SCHEDULE_FILE.exists():
            try:
                data = json.loads(TTS_SCHEDULE_FILE.read_text())
                await db.save_tts_schedule_db(data)
                logger.info("Migrated TTS schedule from JSON to database")
            except:
                pass
        
        if data:
            return {**defaults, **data}
        return defaults
    
    async def save_schedule_config(self, config: Dict[str, Any]):
        """Save TTS schedule configuration to database."""
        import db
        
        config["updated_at"] = datetime.utcnow().isoformat() + "Z"
        await db.save_tts_schedule_db(config)
        # Also write to file for backward compatibility
        try:
            TTS_SCHEDULE_FILE.write_text(json.dumps(config, indent=2))
        except:
            pass
    
    async def load_tts_config(self) -> Dict[str, Any]:
        """Load TTS configuration from database."""
        import db
        
        data = await db.get_tts_config_db()
        if data:
            return data
        
        # Fall back to file
        if TTS_CONFIG_FILE.exists():
            try:
                return json.loads(TTS_CONFIG_FILE.read_text())
            except Exception:
                pass
        return {}
    
    async def start(self):
        """Start the TTS scheduler loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("TTS scheduler started")
    
    async def stop(self):
        """Stop the TTS scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("TTS scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop - checks every minute for scheduled TTS."""
        while self._running:
            try:
                await self._check_and_trigger()
            except Exception as e:
                logger.error(f"TTS scheduler error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _check_and_trigger(self):
        """Check if any scheduled TTS should be triggered.
        
        Uses home-weather style scheduling:
        - hour_pattern: Announce every N hours (1, 2, 3, 4, 6, 12)
        - minute_offset: The minute within the hour to trigger (0-59)
        - start_time/end_time: Active hours window
        - days_of_week: Active days
        """
        schedule_config = await self.load_schedule_config()
        tts_config = await self.load_tts_config()
        
        if not schedule_config.get("enabled"):
            return
        
        if not tts_config.get("enabled"):
            return
        
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_day = now.weekday()  # 0 = Monday
        current_day_abbr = list(DAY_MAP.keys())[current_day]
        
        # Check day filter
        days_of_week = schedule_config.get("days_of_week", [])
        if days_of_week and current_day_abbr not in [d.lower()[:3] for d in days_of_week]:
            return
        
        # Check active hours
        start_time_str = schedule_config.get("start_time", "08:00")
        end_time_str = schedule_config.get("end_time", "21:00")
        
        try:
            start_h, start_m = map(int, start_time_str.split(":"))
            end_h, end_m = map(int, end_time_str.split(":"))
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            current_minutes = current_hour * 60 + current_minute
            
            if not (start_minutes <= current_minutes <= end_minutes):
                return
        except Exception:
            pass  # If parsing fails, proceed anyway
        
        # Check hour pattern - only trigger at hours that match the pattern
        hour_pattern = schedule_config.get("hour_pattern", 3)
        minute_offset = schedule_config.get("minute_offset", 0)
        
        # Generate trigger hours based on pattern (e.g., every 3 hours: 0, 3, 6, 9, 12, 15, 18, 21)
        trigger_hours = list(range(0, 24, hour_pattern))
        
        if current_hour not in trigger_hours:
            return
        
        if current_minute != minute_offset:
            return
        
        # Prevent duplicate triggers within the same minute
        trigger_key = f"pattern_{current_hour}_{current_minute}_{current_day}"
        last_trigger = self._last_triggered.get(trigger_key)
        if last_trigger and (now - last_trigger).total_seconds() < 120:
            return
        
        # Trigger the TTS
        self._last_triggered[trigger_key] = now
        logger.info(f"Triggering scheduled TTS at {current_hour}:{current_minute:02d}")
        
        await self._send_scheduled_tts(tts_config)
    
    async def _send_scheduled_tts(self, tts_config: Dict[str, Any]):
        """Send the scheduled TTS announcement."""
        from ha_tts import send_tts
        
        media_player = tts_config.get("media_player", "").strip()
        if not media_player:
            logger.warning("No media player configured for scheduled TTS")
            return
        
        message = await self._build_bill_summary_message()
        if not message:
            logger.warning("No TTS message generated")
            return
        
        volume = tts_config.get("volume", 0.7)
        wait_for_idle = tts_config.get("wait_for_idle", True)
        tts_service = tts_config.get("tts_service", "tts.google_translate_say")
        
        try:
            success, err = await send_tts(
                message=message,
                media_player=media_player,
                volume=volume,
                wait_for_idle=wait_for_idle,
                tts_service=tts_service,
            )
            if success:
                logger.info("Scheduled TTS sent successfully")
            else:
                logger.error(f"Scheduled TTS failed: {err}")
        except Exception as e:
            logger.error(f"Error sending scheduled TTS: {e}")
    
    async def _build_bill_summary_message(self) -> str:
        """Build the bill summary TTS message using ledger data and message template."""
        try:
            import db

            schedule_config = await self.load_schedule_config()
            tts_config = await self.load_tts_config()
            ledger = await db.get_ledger_data()
            return await build_scheduled_bill_summary_message(ledger, schedule_config, tts_config)
        except Exception as e:
            logger.error(f"Error building bill summary message: {e}")
            return "Your Con Edison bill summary is currently unavailable."


# Global scheduler instance
_scheduler: Optional[TTSScheduler] = None

def get_scheduler() -> TTSScheduler:
    """Get or create the global TTS scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TTSScheduler()
    return _scheduler


async def trigger_new_bill_tts(bill_month_range: str, bill_total: str, due_date: str = ""):
    """Trigger TTS for a new bill."""
    import db
    
    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()
    
    if not tts_config.get("enabled"):
        await db.add_log("debug", "New bill TTS skipped: TTS not enabled")
        return
    
    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "New bill TTS skipped: No media player configured")
        return
    
    template = tts_config.get("messages", {}).get("new_bill", "")
    if not template:
        template = "{prefix} Your new bill for {month_range} is now available. The total is {amount}, due {due_date}."
    
    prefix = tts_config.get("prefix", "Message from Con Edison.")
    
    try:
        message = template.format(
            prefix=prefix,
            month_range=bill_month_range,
            amount=bill_total,
            due_date=due_date or "soon"
        )
    except KeyError:
        message = template
    
    from ha_tts import send_tts
    
    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("New bill TTS sent successfully")
            await db.add_log("info", f"New bill TTS sent: {bill_total} for {bill_month_range}")
        else:
            logger.error(f"New bill TTS failed: {err}")
            await db.add_log("error", f"New bill TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending new bill TTS: {e}")
        await db.add_log("error", f"New bill TTS error: {e}")


async def trigger_payment_received_tts(amount: str, balance: str, payee_name: str = ""):
    """Trigger TTS for a payment received."""
    import db
    
    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()
    
    if not tts_config.get("enabled"):
        await db.add_log("debug", "Payment TTS skipped: TTS not enabled")
        return
    
    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Payment TTS skipped: No media player configured")
        return
    
    template = tts_config.get("messages", {}).get("payment_received", "")
    if not template:
        template = "{prefix} Your payment of {amount} has been received. Your account balance is now {balance}."
    
    prefix = tts_config.get("prefix", "Message from Con Edison.")
    
    try:
        message = template.format(prefix=prefix, amount=amount, balance=balance, payee_name=payee_name)
    except KeyError:
        message = template
    
    from ha_tts import send_tts
    
    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Payment received TTS sent successfully")
            await db.add_log("info", f"Payment TTS sent: {amount} received, balance {balance}")
        else:
            logger.error(f"Payment TTS failed: {err}")
            await db.add_log("error", f"Payment TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending payment TTS: {e}")
        await db.add_log("error", f"Payment TTS error: {e}")


async def trigger_late_fee_tts(late_fee_amount: str):
    """Trigger TTS for a late fee detected on account balance."""
    import db

    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()

    if not tts_config.get("enabled"):
        await db.add_log("debug", "Late fee TTS skipped: TTS not enabled")
        return

    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Late fee TTS skipped: No media player configured")
        return

    template = tts_config.get("messages", {}).get("late_fee", "")
    if not template:
        template = "{prefix} {late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date."

    prefix = tts_config.get("prefix", "Message from Con Edison.")

    try:
        message = template.format(prefix=prefix, late_fee_amount=late_fee_amount)
    except KeyError:
        message = template

    from ha_tts import send_tts

    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Late fee TTS sent successfully")
            await db.add_log("info", f"Late fee TTS sent: {late_fee_amount} added")
        else:
            logger.error(f"Late fee TTS failed: {err}")
            await db.add_log("error", f"Late fee TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending late fee TTS: {e}")
        await db.add_log("error", f"Late fee TTS error: {e}")


async def trigger_payment_claimed_tts(payee_name: str, amount: str, payment_date: str):
    """Trigger TTS when a payee claims a payment (via notification Yes)."""
    import db

    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()

    if not tts_config.get("enabled"):
        await db.add_log("debug", "Payment claimed TTS skipped: TTS not enabled")
        return

    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Payment claimed TTS skipped: No media player configured")
        return

    template = tts_config.get("messages", {}).get("payment_claimed", "")
    if not template:
        template = "{prefix} {payee_name} has claimed a payment of {amount} made on {payment_date}. If this was in error you can unclaim the payment via the account ledger."

    prefix = tts_config.get("prefix", "Message from Con Edison.")

    try:
        message = template.format(prefix=prefix, payee_name=payee_name, amount=amount, payment_date=payment_date)
    except KeyError:
        message = template

    from ha_tts import send_tts

    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Payment claimed TTS sent successfully")
            await db.add_log("info", f"Payment claimed TTS sent: {payee_name} claimed {amount}")
        else:
            logger.error(f"Payment claimed TTS failed: {err}")
            await db.add_log("error", f"Payment claimed TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending payment claimed TTS: {e}")
        await db.add_log("error", f"Payment claimed TTS error: {e}")


async def trigger_payment_unclaimed_tts(payee_name: str, amount: str, payment_date: str):
    """Trigger TTS when a payee unclaims a payment (via Account Ledger)."""
    import db

    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()

    if not tts_config.get("enabled"):
        await db.add_log("debug", "Payment unclaimed TTS skipped: TTS not enabled")
        return

    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Payment unclaimed TTS skipped: No media player configured")
        return

    template = tts_config.get("messages", {}).get("payment_unclaimed", "")
    if not template:
        template = "{prefix} {payee_name} has unclaimed a payment of {amount} made on {payment_date}. If this was in error you can claim the payment via the account ledger."

    prefix = tts_config.get("prefix", "Message from Con Edison.")

    try:
        message = template.format(prefix=prefix, payee_name=payee_name, amount=amount, payment_date=payment_date)
    except KeyError:
        message = template

    from ha_tts import send_tts

    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Payment unclaimed TTS sent successfully")
            await db.add_log("info", f"Payment unclaimed TTS sent: {payee_name} unclaimed {amount}")
        else:
            logger.error(f"Payment unclaimed TTS failed: {err}")
            await db.add_log("error", f"Payment unclaimed TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending payment unclaimed TTS: {e}")
        await db.add_log("error", f"Payment unclaimed TTS error: {e}")


async def trigger_late_fee_tts_duplicate_removed(late_fee_amount: str):
    """Trigger TTS when a late fee is detected on account balance - placeholder to remove duplicate."""
    import db

    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()

    if not tts_config.get("enabled"):
        await db.add_log("debug", "Late fee TTS skipped: TTS not enabled")
        return

    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Late fee TTS skipped: No media player configured")
        return

    template = tts_config.get("messages", {}).get("late_fee", "")
    if not template:
        template = "{prefix} {late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date."

    prefix = tts_config.get("prefix", "Message from Con Edison.")

    try:
        message = template.format(prefix=prefix, late_fee_amount=late_fee_amount)
    except KeyError:
        message = template

    from ha_tts import send_tts

    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Late fee TTS sent successfully")
            await db.add_log("info", f"Late fee TTS sent: {late_fee_amount} added to balance")
        else:
            logger.error(f"Late fee TTS failed: {err}")
            await db.add_log("error", f"Late fee TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending late fee TTS: {e}")
        await db.add_log("error", f"Late fee TTS error: {e}")


async def trigger_late_fee_tts(late_fee_amount: str):
    """Trigger TTS when a late fee is detected on the account balance."""
    import db

    scheduler = get_scheduler()
    tts_config = await scheduler.load_tts_config()

    if not tts_config.get("enabled"):
        await db.add_log("debug", "Late fee TTS skipped: TTS not enabled")
        return

    media_player = tts_config.get("media_player", "").strip()
    if not media_player:
        await db.add_log("debug", "Late fee TTS skipped: No media player configured")
        return

    template = tts_config.get("messages", {}).get("late_fee", "")
    if not template:
        template = "{prefix} {late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date."

    prefix = tts_config.get("prefix", "Message from Con Edison.")

    try:
        message = template.format(
            prefix=prefix,
            late_fee_amount=late_fee_amount,
        )
    except KeyError:
        message = template

    from ha_tts import send_tts

    try:
        success, err = await send_tts(
            message=message,
            media_player=media_player,
            volume=tts_config.get("volume", 0.7),
            wait_for_idle=tts_config.get("wait_for_idle", True),
            tts_service=tts_config.get("tts_service", "tts.google_translate_say"),
        )
        if success:
            logger.info("Late fee TTS sent successfully")
            await db.add_log("info", f"Late fee TTS sent: {late_fee_amount} added")
        else:
            logger.error(f"Late fee TTS failed: {err}")
            await db.add_log("error", f"Late fee TTS failed: {err}")
    except Exception as e:
        logger.error(f"Error sending late fee TTS: {e}")
        await db.add_log("error", f"Late fee TTS error: {e}")
