"""economy.award_print_xp: the payload must match core's DevXpAwardRequest (field `xp`,
route under /api/v1, X-API-Key gate) and carry the stable dedup source_id (print:<job_id>)
— same pattern as the git-commit XP hooks. Network errors must be fail-soft."""
import asyncio
import json

import httpx
import pytest

from app.config import get_settings
from app.economy import award_print_xp


@pytest.fixture(autouse=True)
def core_api_key(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "test-core-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_award_payload_matches_core_contract(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(200, json={"awarded": True})
    assert asyncio.run(award_print_xp("job-7", "benchy")) is True

    (req,) = mock_httpx["requests"]
    assert req.url.path == "/api/v1/economy/award-dev-xp"
    assert req.headers["X-API-Key"] == "test-core-key"
    payload = json.loads(req.content)
    assert payload["source_id"] == "print:job-7"
    assert payload["source"] == "print_genie"
    assert payload["xp"] == 50
    assert payload["discord_id"] == "418075243404591106"


def test_award_skipped_without_api_key(mock_httpx, monkeypatch):
    monkeypatch.delenv("HYPERCODE_API_KEY")
    get_settings.cache_clear()
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False
    assert mock_httpx["requests"] == []  # sink unconfigured — no call attempted


def test_award_reports_core_dedup(mock_httpx):
    # Core replies 200 awarded=false when the source_id was already banked (replay).
    mock_httpx["handler"] = lambda req: httpx.Response(200, json={"awarded": False})
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False


def test_award_fail_soft_on_http_error(mock_httpx):
    def boom(req):
        raise httpx.ConnectError("core unreachable", request=req)

    mock_httpx["handler"] = boom
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False


def test_award_fail_soft_on_4xx(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(422, json={"detail": "bad"})
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False
