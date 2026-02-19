"""
Send TTS via Home Assistant tts.speak service (addon with homeassistant_api).
Uses target TTS entity, media_player_entity_id, message, cache.
Waits for media player idle when configured.
"""
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

HA_BASE = "http://supervisor/core"
IDLE_STATES = ("idle", "unknown", "unavailable")
MAX_WAIT_SECONDS = 300
POLL_INTERVAL = 2


async def _ha_request(
    method: str,
    path: str,
    json_body: Optional[dict] = None,
) -> tuple[int, Optional[dict]]:
    """Call Home Assistant REST API. Returns (status_code, json_response)."""
    import aiohttp
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.warning("SUPERVISOR_TOKEN not set — not running as HA addon")
        return 401, None
    url = f"{HA_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            kwargs = {"headers": headers}
            if json_body is not None:
                kwargs["json"] = json_body
            async with session.request(method, url, **kwargs) as resp:
                data = None
                if resp.content_type and "json" in resp.content_type:
                    try:
                        data = await resp.json()
                    except Exception:
                        pass
                return resp.status, data
    except Exception as e:
        logger.error(f"HA request failed: {e}")
        return 500, None


async def _get_media_player_state(media_player: str) -> Optional[str]:
    """Get current state of media player."""
    status, data = await _ha_request("GET", f"/api/states/{media_player}")
    if status != 200 or not data:
        return None
    return data.get("state")


async def _wait_for_idle(media_player: str) -> bool:
    """Wait until media player is idle. Returns True if idle reached."""
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        state = await _get_media_player_state(media_player)
        if state in IDLE_STATES:
            return True
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        logger.debug(f"Media player {media_player} state={state}, waiting...")
    logger.warning("Timeout waiting for media player idle")
    return False


async def send_tts(
    message: str,
    media_player: str,
    tts_engine: str,
    cache: bool = True,
    volume: float = 0.7,
    wait_for_idle: bool = True,
) -> tuple[bool, str]:
    """
    Send TTS via Home Assistant tts.speak service.
    Uses target TTS entity (tts_engine), media_player_entity_id, message, cache.
    Returns (success, error_message).
    """
    if not message or not media_player:
        return False, "Message and media player required"
    if not tts_engine or not tts_engine.strip():
        return False, "TTS engine (target entity) required"
    media_player = media_player.strip()
    tts_engine = tts_engine.strip()

    if wait_for_idle:
        idle = await _wait_for_idle(media_player)
        if not idle:
            return False, "Media player did not become idle in time"

    status, _ = await _ha_request(
        "POST",
        "/api/services/media_player/volume_set",
        {"entity_id": media_player, "volume_level": max(0.0, min(1.0, float(volume)))},
    )
    if status not in (200, 201):
        logger.warning(f"Volume set returned {status}, continuing with TTS")

    body = {
        "entity_id": tts_engine,
        "media_player_entity_id": media_player,
        "message": message,
        "cache": bool(cache),
    }
    status, resp = await _ha_request("POST", "/api/services/tts/speak", body)
    if status in (200, 201):
        logger.info(f"TTS sent to {media_player} via {tts_engine}")
        return True, ""
    err_msg = "Unknown error"
    if resp and isinstance(resp, dict) and "message" in resp:
        err_msg = resp["message"]
    elif isinstance(resp, str):
        err_msg = resp
    return False, f"TTS service returned {status}: {err_msg}"
