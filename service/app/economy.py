"""Award BROski XP for completed prints via the existing HyperCode core endpoint.

Mirrors the dev-XP git-commit hook pattern: a STABLE source_id so retries/replays bank exactly
once. The core endpoint is the durable-wallet path (broski_wallets / transactions).
"""
from __future__ import annotations

import httpx

from .config import get_settings


async def award_print_xp(job_id: str, model: str) -> bool:
    """Award XP for a successful print. source_id=print:<job_id> dedups at the bank.
    Returns True on a 2xx, False otherwise (fail-soft — a banking hiccup must not crash the webhook)."""
    s = get_settings()
    url = f"{s.core_url.rstrip('/')}{s.award_path}"
    payload = {
        "discord_id": s.owner_discord_id,
        "amount": s.xp_per_success,
        "source_id": f"print:{job_id}",
        "reason": f"Completed print: {model}",
        "category": "print_genie",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code < 300
    except httpx.HTTPError:
        return False
