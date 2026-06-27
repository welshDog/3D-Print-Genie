"""Thin Supabase REST (PostgREST) writer for the print_genie schema.

Uses the service-role key (bypasses RLS) — server-side only. We hit PostgREST directly with httpx
to avoid a heavy SDK dependency. The schema lives under `print_genie`, surfaced via the
`Content-Profile` / `Accept-Profile` headers.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import get_settings

SCHEMA = "print_genie"


def _headers(write: bool = False) -> dict[str, str]:
    s = get_settings()
    h = {
        "apikey": s.supabase_service_role_key,
        "Authorization": f"Bearer {s.supabase_service_role_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if write:
        h["Content-Profile"] = SCHEMA
        h["Prefer"] = "return=representation"
    return h


def _rest_url(table: str) -> str:
    return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/{table}"


async def insert(table: str, row: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_rest_url(table), json=row, headers=_headers(write=True))
        resp.raise_for_status()
        data = resp.json()
        return data[0] if isinstance(data, list) and data else {}


async def update(table: str, row_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.patch(
            f"{_rest_url(table)}?id=eq.{row_id}", json=patch, headers=_headers(write=True)
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if isinstance(data, list) and data else {}


async def select(table: str, query: str = "") -> list[dict[str, Any]]:
    """query is a raw PostgREST query string, e.g. 'order=created_at.desc&limit=10'."""
    url = _rest_url(table)
    if query:
        url = f"{url}?{query}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


# Convenience wrappers ----------------------------------------------------------------------

async def record_event(payload: dict[str, Any]) -> dict[str, Any]:
    return await insert("print_events", payload)


async def upsert_job_result(job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    return await update("print_jobs", job_id, patch)


async def recent_jobs(limit: int = 10) -> list[dict[str, Any]]:
    return await select("print_jobs", f"order=created_at.desc&limit={limit}")
