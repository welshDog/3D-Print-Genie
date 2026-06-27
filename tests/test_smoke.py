"""Dependency-light smoke tests — catch broken imports / route regressions before they hit the Pi.

No network: we test the FastAPI app object, route registration, /health, and the pure Meshy
summarize() logic. Run: pytest
"""
import sys
from pathlib import Path

# Make `app` importable when running pytest from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.meshy import summarize  # noqa: E402

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    # All integrations default to off/unconfigured in CI (no env) — must not crash.
    for key in ("supabase", "meshy", "discord", "auto_pause"):
        assert key in body


def test_expected_routes_registered():
    paths = {r.path for r in app.routes}
    for p in ("/health", "/webhook/printguard", "/preflight", "/jobs", "/status"):
        assert p in paths, f"missing route {p}"


def test_meshy_summarize_pass():
    passed, summary = summarize({"watertight": True, "holes": 0, "non_manifold_edges": 0})
    assert passed is True
    assert "watertight=True" in summary


def test_meshy_summarize_fail_on_holes():
    passed, _ = summarize({"watertight": True, "holes": 3, "non_manifold_edges": 0})
    assert passed is False


def test_meshy_summarize_tolerates_key_drift():
    # Alternate key names should still be read.
    passed, _ = summarize({"is_watertight": True, "hole_count": 0, "non_manifold_edge_count": 0})
    assert passed is True
