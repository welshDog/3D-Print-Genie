"""Phase-4 pause adapter safety rails: unconfigured → no-op, cooldown → no order spam,
missing client → no-op. Never touches the network."""
import asyncio
import time

import app.pause as pause


def test_unconfigured_returns_false(monkeypatch):
    monkeypatch.delenv("ANYCUBIC_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("ANYCUBIC_PRINTER_ID", raising=False)
    assert asyncio.run(pause.try_cloud_pause("job-1")) is False


def test_cooldown_blocks_repeat_pause(monkeypatch):
    monkeypatch.setenv("ANYCUBIC_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("ANYCUBIC_PRINTER_ID", "123")
    monkeypatch.setattr(pause, "_last_pause_ts", time.monotonic())  # just paused
    assert asyncio.run(pause.try_cloud_pause("job-1")) is False


def test_missing_client_path_returns_false(monkeypatch):
    monkeypatch.setenv("ANYCUBIC_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("ANYCUBIC_PRINTER_ID", "123")
    monkeypatch.delenv("ANYCUBIC_CLOUD_API_PATH", raising=False)
    monkeypatch.setattr(pause, "_last_pause_ts", time.monotonic() - 9999)  # cooldown expired
    assert asyncio.run(pause.try_cloud_pause("job-1")) is False
