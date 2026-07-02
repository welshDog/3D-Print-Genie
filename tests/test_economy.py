"""economy.award_print_xp: the payload must carry the stable dedup source_id (print:<job_id>)
— same pattern as the git-commit XP hooks — and network errors must be fail-soft."""
import asyncio
import json

import httpx

from app.economy import award_print_xp


def test_award_payload_carries_dedup_source_id(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(200, json={"ok": True})
    assert asyncio.run(award_print_xp("job-7", "benchy")) is True

    (req,) = mock_httpx["requests"]
    assert req.url.path == "/economy/award-dev-xp"
    payload = json.loads(req.content)
    assert payload["source_id"] == "print:job-7"
    assert payload["category"] == "print_genie"
    assert payload["amount"] == 50
    assert payload["discord_id"] == "418075243404591106"


def test_award_fail_soft_on_http_error(mock_httpx):
    def boom(req):
        raise httpx.ConnectError("core unreachable", request=req)

    mock_httpx["handler"] = boom
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False


def test_award_fail_soft_on_4xx(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(422, json={"detail": "bad"})
    assert asyncio.run(award_print_xp("job-7", "benchy")) is False
