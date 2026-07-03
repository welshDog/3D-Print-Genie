"""Award BROski XP for completed prints via the existing HyperCode core endpoint.

Mirrors the dev-XP git-commit hook pattern: a STABLE source_id so retries/replays bank exactly
once. The core endpoint is the durable-wallet path (broski_wallets / transactions).
"""
from __future__ import annotations

import httpx

from .config import get_settings


async def award_print_xp(job_id: str, model: str) -> bool:
    """Award XP for a successful print. source_id=print:<job_id> dedups at the bank.
    Returns True on a 2xx, False otherwise (fail-soft — a banking hiccup must not crash the webhook).

    Contract = core's DevXpAwardRequest (backend/app/api/v1/endpoints/economy.py): field is `xp`
    (not amount), route lives under /api/v1, and the sink is gated by the master API_KEY sent as
    X-API-Key — same as broski_economy_consumer.py."""
    s = get_settings()
    if not s.core_api_key:
        return False  # sink not configured — fail-soft like the consumer
    url = f"{s.core_url.rstrip('/')}{s.award_path}"
    payload = {
        "discord_id": s.owner_discord_id,
        "xp": s.xp_per_success,
        "source_id": f"print:{job_id}",
        "reason": f"Completed print: {model}",
        "source": "print_genie",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers={"X-API-Key": s.core_api_key})
            if resp.status_code >= 300:
                return False
            # Core replies 200 with awarded=false when source_id was already banked (dedup) —
            # surface that instead of pretending the replay awarded again.
            try:
                return bool(resp.json().get("awarded", True))
            except ValueError:
                return True
    except httpx.HTTPError:
        return False
