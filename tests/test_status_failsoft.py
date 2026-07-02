"""/status is best-effort for the MCP server — a Supabase outage must return 200, not 500."""
import app.main as main_mod
from app.config import get_settings


def _configure_supabase(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "http://sb.test")
    monkeypatch.setattr(settings, "supabase_service_role_key", "svc-key")


def test_status_survives_supabase_outage(client, monkeypatch):
    _configure_supabase(monkeypatch)

    async def boom(limit=1):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(main_mod.db, "recent_jobs", boom)
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["latest_job"] is None


def test_status_returns_latest_job_when_healthy(client, monkeypatch):
    _configure_supabase(monkeypatch)

    async def ok(limit=1):
        return [{"id": "j1", "result": "running", "model": "benchy"}]

    monkeypatch.setattr(main_mod.db, "recent_jobs", ok)
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json()["latest_job"]["id"] == "j1"
