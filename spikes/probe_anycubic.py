#!/usr/bin/env python3
"""Phase-4 spike — Anycubic cloud discovery probe (READ-ONLY by default).

Logs into the Anycubic cloud with your access token, lists your printers, and prints the Kobra X's
printer_id + current project so we can wire up auto-pause. Reuses the maintained
`anycubic_cloud_api` client from hass-anycubic_cloud (DON'T reimplement the app signing).

SETUP
-----
1. git clone https://github.com/WaresWichall/hass-anycubic_cloud somewhere on the Pi.
2. Get a one-time access token (HA config-flow login at uc.makeronline.com, or the repo's login
   helper). Export it.
3. Run:
     export ANYCUBIC_CLOUD_API_PATH=/path/to/custom_components/anycubic_cloud
     export ANYCUBIC_ACCESS_TOKEN=your_token
     python spikes/probe_anycubic.py            # read-only: list printers
     python spikes/probe_anycubic.py --pause    # DANGER: actually pauses the active print (step 3 test)

Requires: aiohttp  (pip install aiohttp)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

API_PATH = os.getenv("ANYCUBIC_CLOUD_API_PATH", "")
ACCESS_TOKEN = os.getenv("ANYCUBIC_ACCESS_TOKEN", "")


def _bootstrap_import():
    if not API_PATH:
        sys.exit(
            "ERROR: set ANYCUBIC_CLOUD_API_PATH to the cloned hass-anycubic_cloud\n"
            "       .../custom_components/anycubic_cloud directory."
        )
    p = Path(API_PATH)
    if not (p / "anycubic_cloud_api").is_dir():
        sys.exit(f"ERROR: {p} does not contain an 'anycubic_cloud_api' package.")
    sys.path.insert(0, str(p))


async def run(do_pause: bool, printer_filter: str) -> int:
    import aiohttp  # noqa: WPS433 (deferred so --help works without it)
    from anycubic_cloud_api.anycubic_api import AnycubicMQTTAPI  # type: ignore

    if not ACCESS_TOKEN:
        print("ERROR: set ANYCUBIC_ACCESS_TOKEN (one-time login token).", file=sys.stderr)
        return 2

    token_cache = Path(tempfile.gettempdir()) / "anycubic_cached_sig_token.token"
    cookie_jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        ac = AnycubicMQTTAPI(
            session=session,
            cookie_jar=cookie_jar,
            auth_token=ACCESS_TOKEN,  # treated as the access-token seed; client logs in + caches
        )
        # Persist the minted session token so we don't re-login every run.
        ac._cached_web_auth_token_path = str(token_cache)  # noqa: SLF001 (documented attr)

        await ac.check_api_tokens()
        printers = await ac.list_my_printers(ignore_init_errors=True)

        if not printers:
            print("No printers on this account. Is the Kobra X added in the Anycubic app?")
            return 1

        print(f"\nFound {len(printers)} printer(s):\n" + "-" * 48)
        target = None
        for pr in printers:
            if pr is None:
                continue
            proj = getattr(pr, "latest_project", None)
            proj_id = getattr(proj, "id", None)
            line = (
                f"  id={pr.id}  name={pr.name!r}  model={pr.machine_name!r}  "
                f"online={getattr(pr, 'printer_online', '?')}  latest_project={proj_id}"
            )
            print(line)
            model = (pr.machine_name or pr.name or "").lower()
            if printer_filter.lower() in model or printer_filter.lower() in (pr.name or "").lower():
                target = pr
        print("-" * 48)

        if not target:
            print(f"\nNo printer matched filter '{printer_filter}'. Use --printer to adjust.")
            return 1

        print(f"\n✅ Target: id={target.id} model={target.machine_name!r}")
        print(f"   → set ANYCUBIC_PRINTER_ID={target.id} in your .env")

        if do_pause:
            proj = getattr(target, "latest_project", None)
            if not proj:
                print("\n⚠️  No active project — start a print first, then re-run --pause.")
                return 1
            print(f"\n⏸️  Sending PAUSE (order_id=2) to project {proj.id} ...")
            msgid = await ac.pause_print(target)
            print(f"   sendOrder msgid={msgid!r} — check the printer screen. Resume from the panel.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Anycubic cloud discovery probe (Phase-4 spike)")
    parser.add_argument("--pause", action="store_true",
                        help="DANGER: actually pause the active print (step-3 command test)")
    parser.add_argument("--printer", default="kobra x",
                        help="substring to match the target printer model/name (default: 'kobra x')")
    args = parser.parse_args()
    _bootstrap_import()
    raise SystemExit(asyncio.run(run(args.pause, args.printer)))


if __name__ == "__main__":
    main()
