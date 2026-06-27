"""Phase 4 — closed-loop pause adapter (Anycubic cloud).

`main.py` imports this lazily, only when AUTO_PAUSE_ENABLED=true. It reuses the maintained
`anycubic_cloud_api` client from hass-anycubic_cloud (we do NOT reimplement the app signing /
access-token login — see spikes/anycubic_cloud_pause.md).

Pause = REST sendOrder(order_id=2) via `client.pause_print(printer)`. Safety rails:
  - OFF unless AUTO_PAUSE_ENABLED=true
  - cooldown so repeated webhooks can't spam orders
  - pause ONLY, never auto-cancel
  - fail-soft: a cloud hiccup must never crash the alert path

Required env (see docker/.env.example):
  ANYCUBIC_CLOUD_API_PATH   path to cloned .../custom_components/anycubic_cloud
  ANYCUBIC_ACCESS_TOKEN     one-time login token (see spike doc)
  ANYCUBIC_PRINTER_ID       from probe_anycubic.py
  PAUSE_COOLDOWN_S          default 120
"""
from __future__ import annotations

import os
import sys
import time
import tempfile
from pathlib import Path

_last_pause_ts: float = 0.0


def _cooldown_active() -> bool:
    cooldown = float(os.getenv("PAUSE_COOLDOWN_S", "120"))
    return (time.monotonic() - _last_pause_ts) < cooldown


def _ensure_client_importable() -> bool:
    api_path = os.getenv("ANYCUBIC_CLOUD_API_PATH", "")
    if not api_path or not (Path(api_path) / "anycubic_cloud_api").is_dir():
        return False
    if api_path not in sys.path:
        sys.path.insert(0, api_path)
    return True


async def try_cloud_pause(job_id: str | None) -> bool:
    """Pause the active Kobra X print via the Anycubic cloud. Returns True only on a confirmed
    sendOrder. Fail-soft everywhere else."""
    global _last_pause_ts

    access_token = os.getenv("ANYCUBIC_ACCESS_TOKEN", "")
    printer_id = os.getenv("ANYCUBIC_PRINTER_ID", "")
    if not access_token or not printer_id:
        return False  # not configured — alert-only

    if _cooldown_active():
        return False  # already paused recently; don't spam orders

    if not _ensure_client_importable():
        return False  # client not installed on this host

    try:
        import aiohttp
        from anycubic_cloud_api.anycubic_api import AnycubicMQTTAPI  # type: ignore

        token_cache = Path(tempfile.gettempdir()) / "anycubic_cached_sig_token.token"
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
            ac = AnycubicMQTTAPI(session=session, cookie_jar=cookie_jar, auth_token=access_token)
            ac._cached_web_auth_token_path = str(token_cache)  # noqa: SLF001
            await ac.check_api_tokens()

            printers = await ac.list_my_printers(ignore_init_errors=True)
            target = next(
                (p for p in printers if p is not None and str(p.id) == str(printer_id)), None
            )
            if target is None or not getattr(target, "latest_project", None):
                return False  # printer not found or nothing actively printing

            msgid = await ac.pause_print(target)  # order_id=2
            if msgid:
                _last_pause_ts = time.monotonic()
                return True
            return False
    except Exception:  # noqa: BLE001 - never crash the webhook on a cloud error
        return False
