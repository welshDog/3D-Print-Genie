"""Print Genie glue service (FastAPI).

Sits between PrintGuard and the HyperCore stack:
  - POST /webhook/printguard  : PrintGuard calls this on a sustained detection. We log the event
                                to Supabase, fire a Discord alert, and (Phase 4, opt-in) request a
                                pause. The Kobra X CANNOT be paused camera-only, so auto-pause is
                                gated behind AUTO_PAUSE_ENABLED + a proven cloud adapter.
  - POST /jobs/{id}/finish    : mark a print finished -> award BROski XP on success.
  - POST /preflight           : run a model URL through Meshy's (async) printability check.
  - GET  /status, /jobs       : surfaced for the MCP server and humans.

Run: uvicorn app.main:app --host 0.0.0.0 --port 8011
"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from . import discord, economy, supabase_client as db
from .config import get_settings
from .meshy import MeshyError, analyze_printability, summarize

app = FastAPI(title="Print Genie", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, Any]:
    s = get_settings()
    return {
        "ok": True,
        "supabase": s.supabase_configured,
        "meshy": s.meshy_configured,
        "discord": bool(s.discord_webhook_url),
        "auto_pause": s.auto_pause_enabled,
    }


def _verify_secret(provided: str | None) -> None:
    expected = get_settings().webhook_secret
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="bad webhook secret")


@app.post("/webhook/printguard")
async def printguard_webhook(
    request: Request,
    x_printgenie_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    """PrintGuard fires this on a sustained defect. Payload shape varies by PrintGuard version,
    so we store the raw body and pull common fields defensively."""
    _verify_secret(x_printgenie_secret)
    payload = await request.json()

    failure_type = payload.get("failure_type") or payload.get("label") or "unknown"
    score = payload.get("score") or payload.get("confidence")
    snapshot_url = payload.get("snapshot_url") or payload.get("image_url")
    job_id = payload.get("job_id")

    # 1) Log the event (fail-soft if Supabase not configured yet).
    if get_settings().supabase_configured:
        try:
            await db.record_event({
                "job_id": job_id,
                "event_type": "detection",
                "score": score,
                "failure_type": failure_type,
                "snapshot_url": snapshot_url,
                "raw": payload,
            })
        except Exception:  # noqa: BLE001 - logging must never crash the alert path
            pass

    # 2) Alert Discord.
    await discord.send_alert(
        title=f"🚨 Print failure: {failure_type}",
        description=f"PrintGuard flagged a sustained defect (score={score}). Get to the printer.",
        level="failure",
        snapshot_url=snapshot_url,
    )

    # 3) Phase 4 (opt-in, off by default). Camera-only cannot pause the Kobra X — only the proven
    #    cloud adapter can. Until then this is a documented no-op.
    paused = False
    if get_settings().auto_pause_enabled:
        from .pause import try_cloud_pause  # local import: optional Phase-4 module
        paused = await try_cloud_pause(job_id)

    return {"ok": True, "alerted": True, "paused": paused}


@app.post("/jobs/{job_id}/finish")
async def finish_job(job_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Mark a print finished. On success, bank BROski XP (deduped by source_id=print:<job_id>)."""
    result = body.get("result", "success")
    model = body.get("model", "unknown")
    awarded = False

    if get_settings().supabase_configured:
        try:
            await db.upsert_job_result(job_id, {"result": result, **{
                k: body[k] for k in ("ended_at", "duration_mins", "notes") if k in body
            }})
        except Exception:  # noqa: BLE001
            pass

    if result == "success":
        awarded = await economy.award_print_xp(job_id, model)
        await discord.send_alert(
            title="✅ Print complete",
            description=f"`{model}` finished. {'+XP banked.' if awarded else ''}",
            level="success",
        )
    return {"ok": True, "result": result, "xp_awarded": awarded}


@app.post("/preflight")
async def preflight(body: dict[str, Any]) -> dict[str, Any]:
    """Run an STL/GLB/OBJ URL through Meshy's async printability check."""
    model_url = body.get("model_url")
    if not model_url:
        raise HTTPException(status_code=400, detail="model_url required")
    try:
        report = await analyze_printability(model_url)
    except MeshyError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    passed, human = summarize(report)
    return {"passed": passed, "summary": human, "report": report}


@app.get("/jobs")
async def jobs(limit: int = 10) -> list[dict[str, Any]]:
    if not get_settings().supabase_configured:
        return []
    return await db.recent_jobs(limit=limit)


@app.get("/status")
async def status() -> dict[str, Any]:
    """Best-effort live snapshot for the MCP server. Pulls the latest job + PrintGuard reachability."""
    s = get_settings()
    latest = (await db.recent_jobs(limit=1))[:1] if s.supabase_configured else []
    return {
        "printguard_base_url": s.printguard_base_url,
        "latest_job": latest[0] if latest else None,
        "auto_pause_enabled": s.auto_pause_enabled,
    }
