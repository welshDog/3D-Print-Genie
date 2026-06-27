"""Print Genie MCP server — lets Claude answer "how's my print going?" from the live log/feed.

Exposes three tools backed by the glue service's REST API:
  - print_status : latest job + PrintGuard reachability
  - recent_jobs  : last N print jobs
  - job_stats    : success/failure rollup

Run (stdio):  python server.py
Point your MCP client (Claude Code / Desktop) at this with env PRINTGENIE_URL set to the glue
service, e.g. http://<pi-ip>:8011

Depends on the `mcp` package (pip install "mcp[cli]") and httpx.
"""
from __future__ import annotations

import os
from collections import Counter

import httpx
from mcp.server.fastmcp import FastMCP

PRINTGENIE_URL = os.getenv("PRINTGENIE_URL", "http://localhost:8011").rstrip("/")

mcp = FastMCP("print-genie")


async def _get(path: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{PRINTGENIE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def print_status() -> dict:
    """Get the current print status: the latest job and whether PrintGuard is reachable."""
    return await _get("/status")


@mcp.tool()
async def recent_jobs(limit: int = 10) -> list:
    """List the most recent print jobs (model, result, failure_type, timing)."""
    return await _get("/jobs", params={"limit": limit})


@mcp.tool()
async def job_stats(limit: int = 100) -> dict:
    """Roll up the last `limit` jobs into success/failure counts and a failure-type breakdown."""
    jobs = await _get("/jobs", params={"limit": limit})
    results = Counter(j.get("result", "unknown") for j in jobs)
    failures = Counter(
        j.get("failure_type") for j in jobs if j.get("result") == "failure" and j.get("failure_type")
    )
    total = len(jobs)
    success = results.get("success", 0)
    return {
        "total": total,
        "by_result": dict(results),
        "success_rate": round(success / total, 3) if total else None,
        "top_failures": dict(failures.most_common(5)),
    }


if __name__ == "__main__":
    mcp.run()
