"""PrintGuard's payload shape varies by version — the webhook must parse both variants and
always alert, and a Supabase failure must never block the Discord alert path."""
import app.main as main_mod
from app.config import get_settings

SECRET_HEADER = {"X-PrintGenie-Secret": "change-me"}  # unset-env default


def _capture_alerts(monkeypatch):
    calls = []

    async def fake_alert(title, description, *, level="failure", snapshot_url=None):
        calls.append({"title": title, "level": level, "snapshot_url": snapshot_url})
        return True

    monkeypatch.setattr(main_mod.discord, "send_alert", fake_alert)
    return calls


def test_canonical_payload_alerts(client, monkeypatch):
    calls = _capture_alerts(monkeypatch)
    resp = client.post(
        "/webhook/printguard",
        json={"failure_type": "warp", "score": 0.77, "snapshot_url": "https://x/f.jpg"},
        headers=SECRET_HEADER,
    )
    assert resp.status_code == 200 and resp.json()["alerted"] is True
    assert calls[0]["title"] == "🚨 Print failure: warp"
    assert calls[0]["snapshot_url"] == "https://x/f.jpg"


def test_alt_key_payload_alerts(client, monkeypatch):
    calls = _capture_alerts(monkeypatch)
    resp = client.post(
        "/webhook/printguard",
        json={"label": "spaghetti", "confidence": 0.9, "image_url": "https://x/a.jpg"},
        headers=SECRET_HEADER,
    )
    assert resp.status_code == 200
    assert calls[0]["title"] == "🚨 Print failure: spaghetti"
    assert calls[0]["snapshot_url"] == "https://x/a.jpg"


def test_supabase_error_never_blocks_alert(client, monkeypatch):
    calls = _capture_alerts(monkeypatch)
    settings = get_settings()
    monkeypatch.setattr(settings, "supabase_url", "http://sb.test")
    monkeypatch.setattr(settings, "supabase_service_role_key", "svc-key")

    async def boom(payload):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(main_mod.db, "record_event", boom)
    resp = client.post(
        "/webhook/printguard", json={"failure_type": "blob"}, headers=SECRET_HEADER
    )
    assert resp.status_code == 200
    assert len(calls) == 1  # alert still fired


def test_auto_pause_off_means_not_paused(client, monkeypatch):
    _capture_alerts(monkeypatch)
    resp = client.post(
        "/webhook/printguard", json={"failure_type": "spaghetti"}, headers=SECRET_HEADER
    )
    assert resp.json()["paused"] is False
