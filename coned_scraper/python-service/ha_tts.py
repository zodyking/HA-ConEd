"""
Send TTS via Home Assistant REST API (addon with homeassistant_api).

Always uses action tts.speak:

    action: tts.speak
    target:
      device_id: <tts device>
    data:
      cache: true
      media_player_entity_id: media_player.example
      message: ...

Falls back to targeting the TTS entity when a device_id cannot be resolved.
Waits for media player idle when configured.
"""
import asyncio
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

HA_BASE = "http://supervisor/core"
IDLE_STATES = ("idle", "unknown", "unavailable")
MAX_WAIT_SECONDS = 300
POLL_INTERVAL = 2
DEVICE_ID_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
LEGACY_SAY_RE = re.compile(r"(_say|_cloud_say)$", re.IGNORECASE)


async def _ha_request(
    method: str,
    path: str,
    json_body: Optional[dict] = None,
) -> tuple[int, Optional[dict | str]]:
    """Call Home Assistant REST API. Returns (status_code, json_or_text)."""
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
                data: Optional[dict | str] = None
                if resp.content_type and "json" in resp.content_type:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = await resp.text()
                else:
                    try:
                        data = (await resp.text()).strip()
                    except Exception:
                        data = None
                return resp.status, data
    except Exception as e:
        logger.error(f"HA request failed: {e}")
        return 500, None


async def _get_media_player_state(media_player: str) -> Optional[str]:
    """Get current state of media player."""
    status, data = await _ha_request("GET", f"/api/states/{media_player}")
    if status != 200 or not isinstance(data, dict):
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


def _is_device_id(value: str) -> bool:
    return bool(value) and bool(DEVICE_ID_RE.fullmatch(value))


def _is_tts_entity(value: str) -> bool:
    return bool(value) and value.startswith("tts.") and not LEGACY_SAY_RE.search(value)


async def resolve_tts_device_id(tts_entity: str) -> str:
    """Resolve a TTS entity to its Home Assistant device_id via the template API."""
    if not tts_entity or not _is_tts_entity(tts_entity):
        return ""
    status, data = await _ha_request(
        "POST",
        "/api/template",
        {"template": "{{ device_id('%s') }}" % tts_entity.replace("'", "")},
    )
    if status not in (200, 201) or data is None:
        logger.warning("Could not resolve device_id for %s (status=%s)", tts_entity, status)
        return ""
    if isinstance(data, dict):
        raw = str(data.get("result") or data.get("message") or "").strip()
    else:
        raw = str(data).strip().strip('"')
    if raw in ("", "None", "none", "null"):
        return ""
    return raw if _is_device_id(raw) else raw


async def send_tts(
    message: str,
    media_player: str,
    volume: float = 0.7,
    wait_for_idle: bool = True,
    tts_service: str = "",
    language: str = "",
    cache: bool = True,
    tts_device_id: str = "",
) -> tuple[bool, str]:
    """
    Send TTS via Home Assistant action tts.speak.

    Target prefers device_id (resolved from the configured TTS entity when needed).
    Data always includes cache, media_player_entity_id, and message.
    """
    if not message or not media_player:
        return False, "Message and media player required"
    media_player = media_player.strip()
    tts_service = (tts_service or "").strip()
    tts_device_id = (tts_device_id or "").strip()

    if _is_device_id(tts_service) and not tts_device_id:
        tts_device_id = tts_service
        tts_service = ""

    if not tts_device_id and _is_tts_entity(tts_service):
        tts_device_id = await resolve_tts_device_id(tts_service)

    if not tts_device_id and not _is_tts_entity(tts_service):
        return False, "No TTS device or entity configured for tts.speak"

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

    service_data: dict[str, Any] = {
        "media_player_entity_id": media_player,
        "message": message,
        "cache": True if cache is None else bool(cache),
    }
    if language and language.strip():
        service_data["language"] = language.strip()

    if tts_device_id:
        service_data["device_id"] = tts_device_id
        target_desc = f"device_id={tts_device_id}"
    else:
        service_data["entity_id"] = tts_service
        target_desc = f"entity_id={tts_service}"

    status, data = await _ha_request(
        "POST",
        "/api/services/tts/speak",
        service_data,
    )

    if status in (200, 201):
        logger.info("TTS sent to %s via tts.speak targeting %s", media_player, target_desc)
        return True, ""

    error_msg = f"tts.speak returned {status}"
    if isinstance(data, dict) and data.get("message"):
        error_msg = f"{error_msg}: {data.get('message')}"
    elif isinstance(data, str) and data:
        error_msg = f"{error_msg}: {data}"

    return False, error_msg


async def speak_from_config(message: str, tts_config: dict) -> tuple[bool, str]:
    """Speak using the saved addon TTS config (always tts.speak)."""
    return await send_tts(
        message=message,
        media_player=(tts_config.get("media_player") or "").strip(),
        volume=tts_config.get("volume", 0.7),
        wait_for_idle=tts_config.get("wait_for_idle", True),
        tts_service=tts_config.get("tts_service") or "",
        tts_device_id=tts_config.get("tts_device_id") or "",
        language=tts_config.get("language") or "",
        cache=True,
    )
