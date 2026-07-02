"""Shared test setup: make `app` importable and provide common fixtures. No network anywhere."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SECRET_HEADER = {"X-PrintGenie-Secret": "change-me"}  # matches the unset-env default


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_httpx(monkeypatch):
    """Route every httpx.AsyncClient created inside app modules through a MockTransport.

    Modules build their own AsyncClient (no transport injection point), so we wrap the
    constructor. Returns a mutable holder: set holder['handler'] to a fn(request) -> Response,
    and inspect holder['requests'] afterwards.
    """
    holder: dict = {"handler": None, "requests": []}
    real_async_client = httpx.AsyncClient

    def transport_handler(request: httpx.Request) -> httpx.Response:
        holder["requests"].append(request)
        if holder["handler"] is None:
            return httpx.Response(200, json={})
        return holder["handler"](request)

    def patched(*args, **kwargs):
        kwargs.pop("transport", None)
        return real_async_client(transport=httpx.MockTransport(transport_handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)
    return holder
