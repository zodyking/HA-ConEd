"""
TTS engine for Con Edison.

Copied from Home-Delivery's working Supervisor path:
POST /api/services/tts/speak with entity_id = TTS engine,
media_player_entity_id = speaker, cache=true, then a legacy
tts/<service> fallback. Volume is restored after speak.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

HA_BASE = "http://supervisor/core"
IDLE_STATES = ("idle", "unknown", "unavailable", "off", "standby")
MAX_WAIT_SECONDS = 300
POLL_INTERVAL = 2


async def _ha_request(
    method: str,
    path: str,
    json_body: Optional[dict[str, Any]] = None,
) -> tuple[int, Optional[dict[str, Any]]]:
    """Make a request to the Home Assistant REST API."""
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
            kwargs: dict[str, Any] = {"headers": headers}
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


async def _get_media_player_state(entity_id: str) -> Optional[str]:
    status, data = await _ha_request("GET", f"/api/states/{entity_id}")
    if status != 200 or not data:
        return None
    return data.get("state")


async def _get_volume_level(entity_id: str) -> Optional[float]:
    status, data = await _ha_request("GET", f"/api/states/{entity_id}")
    if status != 200 or not data:
        return None
    attrs = data.get("attributes") or {}
    vol = attrs.get("volume_level")
    try:
        return float(vol) if vol is not None else None
    except (TypeError, ValueError):
        return None


async def _wait_for_idle(entity_id: str) -> bool:
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        state = await _get_media_player_state(entity_id)
        if state in IDLE_STATES:
            return True
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    logger.warning(f"Timeout waiting for {entity_id} to become idle")
    return False


async def _set_volume(entity_id: str, volume: float) -> bool:
    status, _ = await _ha_request(
        "POST",
        "/api/services/media_player/volume_set",
        {
            "entity_id": entity_id,
            "volume_level": max(0.0, min(1.0, float(volume))),
        },
    )
    return status == 200


async def send_tts(
    message: str,
    media_player: str,
    volume: float = 0.7,
    wait_for_idle: bool = True,
    tts_service: str = "",
    language: str = "",
    cache: bool = True,
    tts_device_id: str = "",
    preroll_ms: int = 0,
) -> tuple[bool, str]:
    """
    Send TTS via Home Assistant tts.speak, matching Home-Delivery.

    Target is the TTS engine entity_id (not a device_id). tts_device_id is
    ignored for the service call so we stay on the working HA path.
    """
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.warning("Cannot send TTS: SUPERVISOR_TOKEN not available")
        return False, "SUPERVISOR_TOKEN not available"

    if not message or not media_player:
        return False, "Message and media player required"

    media_player = media_player.strip()
    tts_entity = (tts_service or "").strip() or (tts_device_id or "").strip()
    if not tts_entity:
        return False, "No TTS entity configured"

    logger.info(f"Sending TTS to {media_player}: {message[:50]}...")

    previous_volume = await _get_volume_level(media_player)

    if wait_for_idle:
        await _wait_for_idle(media_player)

    await _set_volume(media_player, volume)

    if preroll_ms > 0:
        await asyncio.sleep(preroll_ms / 1000)

    service_data: dict[str, Any] = {
        "entity_id": tts_entity,
        "media_player_entity_id": media_player,
        "message": message,
        "cache": bool(cache),
    }
    if language and str(language).strip():
        service_data["language"] = str(language).strip()

    status, data = await _ha_request("POST", "/api/services/tts/speak", service_data)
    ok = status == 200

    if not ok:
        tts_service_name = tts_entity.replace("tts.", "", 1) if tts_entity.startswith("tts.") else tts_entity
        legacy_data: dict[str, Any] = {
            "entity_id": media_player,
            "message": message,
        }
        if language and str(language).strip():
            legacy_data["language"] = str(language).strip()
        status, data = await _ha_request(
            "POST",
            f"/api/services/tts/{tts_service_name}",
            legacy_data,
        )
        ok = status == 200

    if previous_volume is not None:
        await asyncio.sleep(0.5)
        await _set_volume(media_player, previous_volume)

    if ok:
        logger.info("TTS sent successfully to %s via tts.speak entity_id=%s", media_player, tts_entity)
        return True, ""

    error_msg = f"tts.speak returned {status}"
    if isinstance(data, dict) and data.get("message"):
        error_msg = f"{error_msg}: {data.get('message')}"
    logger.error("TTS failed for %s: %s", media_player, error_msg)
    return False, error_msg


async def speak_from_config(message: str, tts_config: dict) -> tuple[bool, str]:
    """Speak using the saved addon TTS config (Home-Delivery tts.speak path)."""
    return await send_tts(
        message=message,
        media_player=(tts_config.get("media_player") or "").strip(),
        volume=tts_config.get("volume", 0.7),
        wait_for_idle=tts_config.get("wait_for_idle", True),
        tts_service=tts_config.get("tts_service") or "",
        tts_device_id=tts_config.get("tts_device_id") or "",
        language=tts_config.get("language") or "",
        cache=True,
        preroll_ms=int(tts_config.get("preroll_ms") or 0),
    )
