"""The job spine must self-heal: PrintGuard never announces job starts, so the first sight of a
job_id creates its print_jobs row (else the print_events FK rejects the insert and the fail-soft
callers drop the event on the floor), and a finish for an unregistered job still lands via upsert."""
import asyncio
import json

import httpx
import pytest

from app import supabase_client as db
from app.config import get_settings


@pytest.fixture(autouse=True)
def supabase_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_record_event_ensures_job_row_first(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(201, json=[{"id": "j-1"}])
    asyncio.run(db.record_event({"job_id": "j-1", "event_type": "detection"}))

    ensure, event = mock_httpx["requests"]
    assert ensure.url.path.endswith("/print_jobs")
    assert "resolution=ignore-duplicates" in ensure.headers["Prefer"]  # never clobber a real row
    assert json.loads(ensure.content)["id"] == "j-1"
    assert event.url.path.endswith("/print_events")


def test_record_event_without_job_id_skips_ensure(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(201, json=[{}])
    asyncio.run(db.record_event({"job_id": None, "event_type": "detection"}))

    (event,) = mock_httpx["requests"]
    assert event.url.path.endswith("/print_events")


def test_finish_upserts_unregistered_job(mock_httpx):
    mock_httpx["handler"] = lambda req: httpx.Response(201, json=[{"id": "j-2"}])
    asyncio.run(db.upsert_job_result("j-2", {"result": "success", "model": "benchy"}))

    (req,) = mock_httpx["requests"]
    assert req.method == "POST" and "on_conflict=id" in str(req.url)
    assert "resolution=merge-duplicates" in req.headers["Prefer"]
    payload = json.loads(req.content)
    assert payload["id"] == "j-2" and payload["result"] == "success"
    assert payload["model"] == "benchy"  # caller's model wins over the 'unknown' placeholder
