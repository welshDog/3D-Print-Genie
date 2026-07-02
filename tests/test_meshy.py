"""Meshy preflight client: the async create → poll flow, terminal states, and the timeout.
All via httpx.MockTransport — no network, fast polls."""
import asyncio

import httpx
import pytest

from app.config import get_settings
from app.meshy import MeshyError, analyze_printability


@pytest.fixture
def meshy_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "meshy_api_key", "test-key")


def test_no_key_raises():
    settings = get_settings()
    assert not settings.meshy_configured  # CI/local default: no env
    with pytest.raises(MeshyError, match="MESHY_API_KEY"):
        asyncio.run(analyze_printability("https://x/y.stl"))


def test_create_then_poll_until_succeeded(mock_httpx, meshy_key):
    polls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["Authorization"] == "Bearer test-key"
        if req.method == "POST":
            return httpx.Response(200, json={"result": "task-1"})
        polls["n"] += 1
        if polls["n"] < 3:
            return httpx.Response(200, json={"status": "IN_PROGRESS"})
        return httpx.Response(
            200, json={"status": "SUCCEEDED", "watertight": True, "holes": 0}
        )

    mock_httpx["handler"] = handler
    report = asyncio.run(
        analyze_printability("https://x/y.stl", timeout_s=5, poll_interval_s=0.01)
    )
    assert report["watertight"] is True
    assert polls["n"] == 3


def test_failed_status_raises(mock_httpx, meshy_key):
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"result": "task-1"})
        return httpx.Response(200, json={"status": "FAILED"})

    mock_httpx["handler"] = handler
    with pytest.raises(MeshyError, match="FAILED"):
        asyncio.run(analyze_printability("https://x/y.stl", poll_interval_s=0.01))


def test_never_terminal_times_out(mock_httpx, meshy_key):
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"result": "task-1"})
        return httpx.Response(200, json={"status": "PENDING"})

    mock_httpx["handler"] = handler
    with pytest.raises(MeshyError, match="timed out"):
        asyncio.run(
            analyze_printability("https://x/y.stl", timeout_s=0.05, poll_interval_s=0.01)
        )


def test_missing_task_id_raises(mock_httpx, meshy_key):
    mock_httpx["handler"] = lambda req: httpx.Response(200, json={})
    with pytest.raises(MeshyError, match="task_id"):
        asyncio.run(analyze_printability("https://x/y.stl"))
