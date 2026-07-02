"""Fake printer — drive the Print Genie glue loop without a Kobra X or a Pi.

Fires realistic PrintGuard-style webhook payloads (and job-finish events) at a running glue
service so Phase 2/3 can be proven end-to-end before the hardware lands. Everything is
fail-soft in the service, so this works even with zero creds configured (Supabase/Discord/
economy calls just no-op).

Usage (glue service running, e.g. `uvicorn app.main:app --port 8011` from service/):

    python tools/simulate_printguard.py detection                  # one spaghetti alert
    python tools/simulate_printguard.py detection --failure warp --score 0.91
    python tools/simulate_printguard.py finish my-job-1            # success -> XP path
    python tools/simulate_printguard.py finish my-job-1 --result failure
    python tools/simulate_printguard.py preflight https://example.com/benchy.stl
    python tools/simulate_printguard.py scenario                   # full print lifecycle

Env / flags: --url (PRINTGENIE_URL, default http://localhost:8011),
             --secret (PRINTGENIE_WEBHOOK_SECRET, default change-me).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

import httpx


def _client(url: str) -> httpx.Client:
    return httpx.Client(base_url=url.rstrip("/"), timeout=30.0)


def _show(label: str, resp: httpx.Response) -> None:
    body: object
    try:
        body = resp.json()
    except ValueError:
        body = resp.text[:200]
    print(f"[{resp.status_code}] {label}: {json.dumps(body, default=str)}")
    if resp.status_code >= 400:
        sys.exit(1)


def send_detection(client: httpx.Client, secret: str, *, failure: str, score: float,
                   job_id: str | None, alt_keys: bool = False) -> None:
    """PrintGuard's payload shape varies by version — the service parses defensively.
    alt_keys exercises the label/confidence/image_url variant."""
    if alt_keys:
        payload = {
            "label": failure,
            "confidence": score,
            "image_url": "https://example.com/frames/latest.jpg",
            "job_id": job_id,
        }
    else:
        payload = {
            "failure_type": failure,
            "score": score,
            "snapshot_url": "https://example.com/frames/latest.jpg",
            "job_id": job_id,
        }
    resp = client.post("/webhook/printguard", json=payload,
                       headers={"X-PrintGenie-Secret": secret})
    _show(f"detection ({failure}, score={score})", resp)


def send_finish(client: httpx.Client, secret: str, job_id: str, *, result: str,
                model: str) -> None:
    resp = client.post(f"/jobs/{job_id}/finish",
                       json={"result": result, "model": model, "duration_mins": 42},
                       headers={"X-PrintGenie-Secret": secret})
    _show(f"finish {job_id} ({result})", resp)


def send_preflight(client: httpx.Client, secret: str, model_url: str) -> None:
    resp = client.post("/preflight", json={"model_url": model_url},
                       headers={"X-PrintGenie-Secret": secret})
    _show("preflight", resp)


def run_scenario(client: httpx.Client, secret: str) -> None:
    """Full fake print lifecycle: two sustained detections, then a successful finish
    (exercises Supabase event log, Discord alert, and the deduped XP path)."""
    job_id = str(uuid.uuid4())
    print(f"-- scenario job_id={job_id}")
    send_detection(client, secret, failure="spaghetti", score=0.82, job_id=job_id)
    time.sleep(0.5)
    send_detection(client, secret, failure="spaghetti", score=0.88, job_id=job_id,
                   alt_keys=True)
    time.sleep(0.5)
    send_finish(client, secret, job_id, result="success", model="benchy-sim")
    # Replay the finish: XP must bank exactly once (source_id dedup at the core).
    send_finish(client, secret, job_id, result="success", model="benchy-sim")
    print("-- scenario done (second finish should show the dedup: xp_awarded reflects the "
          "core's SETNX-style gate once real creds are wired)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    # 127.0.0.1, not localhost: on Windows localhost can resolve to ::1 while uvicorn binds IPv4.
    parser.add_argument("--url", default=os.getenv("PRINTGENIE_URL", "http://127.0.0.1:8011"))
    parser.add_argument("--secret",
                        default=os.getenv("PRINTGENIE_WEBHOOK_SECRET", "change-me"))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_det = sub.add_parser("detection", help="fire one PrintGuard-style failure webhook")
    p_det.add_argument("--failure", default="spaghetti")
    p_det.add_argument("--score", type=float, default=0.85)
    p_det.add_argument("--job-id", default=None)
    p_det.add_argument("--alt-keys", action="store_true",
                       help="use the label/confidence payload variant")

    p_fin = sub.add_parser("finish", help="mark a job finished (success banks XP)")
    p_fin.add_argument("job_id")
    p_fin.add_argument("--result", default="success",
                       choices=["success", "failure", "cancelled"])
    p_fin.add_argument("--model", default="benchy-sim")

    p_pre = sub.add_parser("preflight", help="run a model URL through Meshy preflight")
    p_pre.add_argument("model_url")

    sub.add_parser("scenario", help="full lifecycle: detections + finish + dedup replay")

    args = parser.parse_args()
    with _client(args.url) as client:
        if args.cmd == "detection":
            send_detection(client, args.secret, failure=args.failure, score=args.score,
                           job_id=args.job_id, alt_keys=args.alt_keys)
        elif args.cmd == "finish":
            send_finish(client, args.secret, args.job_id, result=args.result,
                        model=args.model)
        elif args.cmd == "preflight":
            send_preflight(client, args.secret, args.model_url)
        elif args.cmd == "scenario":
            run_scenario(client, args.secret)


if __name__ == "__main__":
    main()
