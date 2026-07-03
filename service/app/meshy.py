"""Meshy STL preflight client — CORRECTED async flow.

The `the idea` doc used a synchronous `POST /openapi/v1/3d-model/analyze-printability` returning
the result inline. That is WRONG. The real Analyze-Printability API is async:

    POST /openapi/v1/print/analyze   -> { "result": "<task_id>" }   (create)
    GET  /openapi/v1/print/analyze/<task_id>  -> { status, watertight, holes, ... }  (poll)

It is free (consumes no credits). Endpoint paths can shift between Meshy releases — if a call
404s, check https://docs.meshy.ai/en/api/ai and adjust BASE/paths here in ONE place.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import get_settings

CREATE_PATH = "/openapi/v1/print/analyze"
POLL_PATH = "/openapi/v1/print/analyze/{task_id}"
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED"}


class MeshyError(RuntimeError):
    pass


async def analyze_printability(
    model_url: str,
    *,
    timeout_s: float = 120.0,
    poll_interval_s: float = 3.0,
) -> dict[str, Any]:
    """Run an STL/GLB/OBJ through Meshy's FDM printability check. Returns the final report dict
    (watertightness, holes, non-manifold edges, volume, ...). Raises MeshyError on failure."""
    settings = get_settings()
    if not settings.meshy_configured:
        raise MeshyError("MESHY_API_KEY not set — preflight disabled")

    headers = {"Authorization": f"Bearer {settings.meshy_api_key}"}
    base = settings.meshy_base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=30.0) as client:
        create = await client.post(
            f"{base}{CREATE_PATH}", json={"model_url": model_url}, headers=headers
        )
        if create.status_code >= 400:
            raise MeshyError(f"create failed {create.status_code}: {create.text}")
        task_id = (create.json() or {}).get("result")
        if not task_id:
            raise MeshyError(f"no task_id in response: {create.text}")

        deadline = asyncio.get_event_loop().time() + timeout_s
        while True:
            poll = await client.get(
                f"{base}{POLL_PATH.format(task_id=task_id)}", headers=headers
            )
            if poll.status_code >= 400:
                raise MeshyError(f"poll failed {poll.status_code}: {poll.text}")
            body = poll.json() or {}
            status = str(body.get("status", "")).upper()
            if status in TERMINAL:
                if status != "SUCCEEDED":
                    raise MeshyError(f"analysis ended {status}: {body}")
                return body
            if asyncio.get_event_loop().time() > deadline:
                raise MeshyError(f"timed out after {timeout_s}s (last status={status})")
            await asyncio.sleep(poll_interval_s)


def summarize(report: dict[str, Any]) -> tuple[bool, str]:
    """Collapse a Meshy report into (passed, human_summary). Tolerant of key drift.

    Live API (verified 2026-07-03) nests the numbers under printability.metrics with an
    is_watertight key; older/flat shapes are kept as fallbacks."""
    printability = report.get("printability") or {}
    metrics = printability.get("metrics") or report
    watertight = metrics.get("is_watertight", metrics.get("watertight"))
    holes = metrics.get("holes", metrics.get("hole_count"))
    non_manifold = metrics.get("non_manifold_edges", metrics.get("non_manifold_edge_count"))
    passed = bool(watertight) and not holes and not non_manifold
    summary = f"watertight={watertight} holes={holes} non_manifold_edges={non_manifold}"
    if printability.get("status"):
        summary += (
            f" (meshy status={printability['status']},"
            f" errors={printability.get('error_count')},"
            f" warnings={printability.get('warning_count')})"
        )
    return passed, summary
