"""
TTS queue and logging. All TTS from the app goes through here.
Processes one at a time, logs every send (success or fail).
"""
import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_LOGS = 500
_logs: deque = deque(maxlen=MAX_LOGS)
_queue: List[Dict[str, Any]] = []
_lock = asyncio.Lock()
_processor_started = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_tts(
    source: str,
    message: str,
    media_players: list,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Append a TTS log entry."""
    entry = {
        "ts": _utc_now_iso(),
        "source": source,
        "message": message[:200] + ("..." if len(message) > 200 else ""),
        "media_players": media_players,
        "success": success,
        "error": error,
    }
    _logs.append(entry)


def get_logs() -> List[Dict[str, Any]]:
    """Return TTS logs (newest last)."""
    return list(_logs)


def get_queue() -> List[Dict[str, Any]]:
    """Return current queue (copy)."""
    return list(_queue)


async def enqueue_tts(
    source: str,
    message: str,
    media_players: list,
    tts_engine: str,
    cache: bool = True,
    wait_for_idle: bool = True,
) -> bool:
    """
    Add TTS to queue. Returns immediately. Processor will send when ready.
    Returns True if queued successfully.
    """
    async with _lock:
        item = {
            "source": source,
            "message": message,
            "media_players": media_players,
            "tts_engine": tts_engine,
            "cache": cache,
            "wait_for_idle": wait_for_idle,
        }
        _queue.append(item)
    return True


async def _process_one() -> bool:
    """Process one item from queue. Returns True if an item was processed."""
    async with _lock:
        if not _queue:
            return False
        item = _queue.pop(0)
    source = item.get("source", "unknown")
    message = item.get("message", "")
    media_players = item.get("media_players", [])
    tts_engine = item.get("tts_engine", "")
    cache = item.get("cache", True)
    wait_for_idle = item.get("wait_for_idle", True)
    player_ids = [
        (p.get("entity_id") or "").strip()
        for p in media_players
        if isinstance(p, dict) and (p.get("entity_id") or "").strip()
    ]
    success = False
    err = None
    try:
        import os
        if os.environ.get("SUPERVISOR_TOKEN"):
            from ha_tts import send_tts
            success, err = await send_tts(
                message=message,
                media_players=media_players,
                tts_engine=tts_engine,
                cache=cache,
                wait_for_idle=wait_for_idle,
            )
        else:
            from mqtt_client import get_mqtt_client
            mqtt = get_mqtt_client()
            if mqtt and mqtt.enabled:
                for p in media_players:
                    mp = (p.get("entity_id") or "").strip()
                    if mp:
                        await mqtt.publish_tts_request(
                            message=message,
                            media_player=mp,
                            volume=float(p.get("volume", 0.7)),
                            wait_for_idle=wait_for_idle,
                        )
                success = True
            else:
                err = "Not in HA addon and MQTT not configured"
        log_tts(source, message, player_ids, success, err if not success else None)
        return True  # item was processed
    except Exception as e:
        logger.exception("TTS send failed")
        log_tts(source, message, player_ids, False, str(e))
        return True


async def _processor() -> None:
    """Background task: process TTS queue."""
    while True:
        processed = await _process_one()
        if not processed:
            await asyncio.sleep(0.5)
        # else: immediately try next (no delay between items)


def start_processor() -> None:
    """Start the TTS queue processor task."""
    global _processor_started
    if _processor_started:
        return
    _processor_started = True
    asyncio.create_task(_processor())
    logger.info("TTS queue processor started")
