"""MCP job_stats rollup logic (success rate + failure breakdown) with a canned jobs feed."""
import asyncio
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("mcp")

_SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
_spec = importlib.util.spec_from_file_location("printgenie_mcp_server", _SERVER_PATH)
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)

JOBS = [
    {"result": "success"},
    {"result": "success"},
    {"result": "failure", "failure_type": "spaghetti"},
    {"result": "failure", "failure_type": "spaghetti"},
    {"result": "failure", "failure_type": "warp"},
]


def test_job_stats_rollup(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/jobs"
        return JOBS

    monkeypatch.setattr(server, "_get", fake_get)
    stats = asyncio.run(server.job_stats(limit=100))
    assert stats["total"] == 5
    assert stats["by_result"] == {"success": 2, "failure": 3}
    assert stats["success_rate"] == 0.4
    assert stats["top_failures"] == {"spaghetti": 2, "warp": 1}


def test_job_stats_empty_feed(monkeypatch):
    async def fake_get(path, params=None):
        return []

    monkeypatch.setattr(server, "_get", fake_get)
    stats = asyncio.run(server.job_stats())
    assert stats["total"] == 0
    assert stats["success_rate"] is None
