"""The /finish → BROski XP wiring: success awards exactly through economy with the job's id,
non-success never touches the bank."""
import app.main as main_mod

SECRET_HEADER = {"X-PrintGenie-Secret": "change-me"}  # unset-env default


def _wire_fakes(monkeypatch, award_result=True):
    awards, alerts = [], []

    async def fake_award(job_id, model):
        awards.append((job_id, model))
        return award_result

    async def fake_alert(title, description, *, level="failure", snapshot_url=None):
        alerts.append(level)
        return True

    monkeypatch.setattr(main_mod.economy, "award_print_xp", fake_award)
    monkeypatch.setattr(main_mod.discord, "send_alert", fake_alert)
    return awards, alerts


def test_success_awards_xp_for_job(client, monkeypatch):
    awards, alerts = _wire_fakes(monkeypatch)
    resp = client.post(
        "/jobs/job-42/finish",
        json={"result": "success", "model": "benchy"},
        headers=SECRET_HEADER,
    )
    body = resp.json()
    assert resp.status_code == 200 and body["xp_awarded"] is True
    assert awards == [("job-42", "benchy")]
    assert alerts == ["success"]


def test_failure_never_touches_the_bank(client, monkeypatch):
    awards, alerts = _wire_fakes(monkeypatch)
    resp = client.post(
        "/jobs/job-42/finish",
        json={"result": "failure", "model": "benchy"},
        headers=SECRET_HEADER,
    )
    assert resp.status_code == 200 and resp.json()["xp_awarded"] is False
    assert awards == [] and alerts == []


def test_award_failure_is_fail_soft(client, monkeypatch):
    _wire_fakes(monkeypatch, award_result=False)
    resp = client.post(
        "/jobs/job-42/finish", json={"result": "success"}, headers=SECRET_HEADER
    )
    assert resp.status_code == 200 and resp.json()["xp_awarded"] is False
