"""Discord webhook alerts. Reuses the existing HyperCore Discord — no new Telegram bot needed."""
from __future__ import annotations

import httpx

from .config import get_settings

_COLORS = {"failure": 0xE74C3C, "paused": 0xF1C40F, "success": 0x2ECC71}


async def send_alert(title: str, description: str, *, level: str = "failure",
                     snapshot_url: str | None = None) -> bool:
    """Post an embed to the configured Discord channel webhook. Fail-soft."""
    s = get_settings()
    if not s.discord_webhook_url:
        return False
    embed: dict = {
        "title": title,
        "description": description,
        "color": _COLORS.get(level, 0x95A5A6),
    }
    if snapshot_url:
        embed["image"] = {"url": snapshot_url}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(s.discord_webhook_url, json={"embeds": [embed]})
            return resp.status_code < 300
    except httpx.HTTPError:
        return False
