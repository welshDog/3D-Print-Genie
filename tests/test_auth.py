"""Every mutating endpoint must require the shared secret — an open /finish would let anyone
on the LAN bank BROski XP, and an open /preflight would burn Meshy quota."""
SECRET_HEADER = {"X-PrintGenie-Secret": "change-me"}  # unset-env default


def test_webhook_rejects_missing_secret(client):
    resp = client.post("/webhook/printguard", json={"failure_type": "spaghetti"})
    assert resp.status_code == 401


def test_webhook_rejects_wrong_secret(client):
    resp = client.post(
        "/webhook/printguard",
        json={"failure_type": "spaghetti"},
        headers={"X-PrintGenie-Secret": "nope"},
    )
    assert resp.status_code == 401


def test_webhook_accepts_correct_secret(client):
    resp = client.post(
        "/webhook/printguard",
        json={"failure_type": "spaghetti", "score": 0.9},
        headers=SECRET_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_finish_requires_secret(client):
    resp = client.post("/jobs/some-job/finish", json={"result": "success"})
    assert resp.status_code == 401


def test_preflight_requires_secret(client):
    resp = client.post("/preflight", json={"model_url": "https://x/y.stl"})
    assert resp.status_code == 401


def test_read_endpoints_stay_open(client):
    # MCP server reads these without a secret — keep them open (read-only).
    assert client.get("/health").status_code == 200
    assert client.get("/jobs").status_code == 200
    assert client.get("/status").status_code == 200
