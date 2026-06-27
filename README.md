# 🧞 Print Genie

> HyperCore-native AI **Print Guardian** for the Anycubic **Kobra X**.
> STL → preflight → print → AI camera watch → **Discord alert** → **Supabase** job log →
> queryable by **Claude (MCP)** → **BROski XP** on success. Phase-4 spike: closed-loop auto-pause.

This README is the **authoritative doc** for the project. The original brainstorm lives in `the idea`
(kept for history) but contains a few **factual errors** — see [Corrections](#-corrections-read-this)
before copy-pasting anything from it.

---

## 🧠 Why this exists

The Kobra X is a great printer but it's **locked down**: closed Anycubic K4 Klipper port, **no**
Rinkhals / OctoPrint / Moonraker community access. That means the usual self-hosted monitoring tools
(Obico, OctoPrint plugins) can't drive it. The only realistic path is **camera-only AI failure
detection** — and the best open tool for that is [PrintGuard](https://github.com/oliverbravery/PrintGuard).

Print Genie wraps PrintGuard in the HyperCore ecosystem instead of bolting on a generic Telegram bot:
Discord for alerts, Supabase for the job log, an MCP server so Claude can answer *"how's my print
going?"*, and the existing BROski economy to reward finished prints.

---

## ⚠️ Corrections (READ THIS)

The `the idea` doc was AI-generated and got these wrong — **do not** copy-paste them:

| # | Claim in `the idea` | Reality |
|---|---------------------|---------|
| 1 | "Action on failure: **Pause**" works camera-only | ❌ PrintGuard's auto-pause only fires *through* an OctoPrint/Klipper/Bambu connection. On a stock Kobra X there is **no control channel**, so camera-only = **detect + alert only**. Closed-loop pause is a separate build (Phase 4). |
| 2 | Meshy `POST /openapi/v1/3d-model/analyze-printability` (sync) | ❌ Real call is `POST /openapi/v1/print/analyze` → returns a `task_id`, then **poll/SSE** for the result. It's **async**. Free / no credits. |
| 3 | PrintGuard is a finished product | ⚠️ It's **v1.0.0b1 — a beta**. Good, not bulletproof. Keep **Notify-only** until you know the false-positive rate. |
| 4 | `devices: /dev/video0` in compose | ✅ Correct for the **Pi/Linux** host. Irrelevant on Windows. We run on the Pi, so it's fine. |

---

## 🏗️ Architecture

```
Kobra X (LAN Mode)            Raspberry Pi 4/5                 HyperCore stack
  └─ USB webcam ───────────▶  PrintGuard (Docker :8000)        ├─ Discord (existing bots)
                              AI scores every frame            ├─ Supabase (job log tables)
                                   │ webhook on failure        ├─ MCP server (Claude queries)
                                   ▼                           └─ core /economy/award-dev-xp
                              Print Genie service ──────────────▶ (BROski XP per success)
                              (FastAPI, the glue)
                                   │  Phase 4 spike
                                   ▼
                              Anycubic Cloud MQTT ──▶ pause/cancel (unofficial)
```

PrintGuard is consumed as an **upstream Docker image** — we do **not** fork it.

---

## 📁 Layout

```
3d Print Genie/
├─ README.md                 ← you are here (authoritative)
├─ the idea                  ← original brainstorm (history; has errors above)
├─ .gitignore
├─ docker/
│  ├─ docker-compose.yml     ← PrintGuard on the Pi (Phase 1)
│  └─ .env.example
├─ db/
│  └─ migrations/
│     └─ 0001_print_genie.sql  ← print_jobs / print_events (apply via MCP apply_migration)
├─ service/                  ← FastAPI glue (Phase 2/3)
│  ├─ app/
│  │  ├─ main.py             ← webhook receiver + REST
│  │  ├─ config.py           ← env settings
│  │  ├─ supabase_client.py  ← job/event writes
│  │  ├─ meshy.py            ← CORRECT async preflight client
│  │  └─ economy.py          ← BROski XP caller (source_id dedup)
│  ├─ requirements.txt
│  └─ .env.example
├─ mcp/                      ← Print Genie MCP server (Phase 3)
│  ├─ server.py
│  └─ requirements.txt
└─ spikes/
   └─ anycubic_cloud_pause.md  ← Phase 4 research + adapter plan
```

---

## 🚦 Roadmap (phased)

- **Phase 0 — Physical + browser demo (no code).** Tune the Kobra X (wash plate, belt tension,
  eccentric nuts, lube rails, first-layer calibration). Mount webcam. Try
  [the browser PrintGuard demo](https://oliverbravery.github.io/PrintGuard) to sanity-check detection
  on your real bed/lighting. Enable **LAN Mode** (Settings → Network → LAN Mode).
- **Phase 1 — Detection + Discord alert** *(tonight win)*. `docker/docker-compose.yml` → PrintGuard on
  the Pi → camera-only monitor → **Discord webhook** alert + snapshot. Action = **Notify only**.
- **Phase 2 — Supabase job log + Meshy preflight.** FastAPI webhook writes `print_events`; finished
  prints become `print_jobs`; Meshy preflight verdict stored per job.
- **Phase 3 — MCP + economy.** MCP tools (`print_status`, `recent_jobs`, `job_stats`); `success`
  events award BROski XP via core `/economy/award-dev-xp` with `source_id=print:<job_id>` dedup.
- **Phase 4 — Closed-loop auto-pause spike.** Investigate Anycubic **cloud** MQTT pause/cancel (proven
  on the sibling Kobra S1; schema unconfirmed on the X). See `spikes/anycubic_cloud_pause.md`.

---

## 🔧 Quick start (Phase 1, on the Pi)

```bash
# On a fresh Raspberry Pi OS Lite 64-bit, with Docker installed:
cd ~ && git clone <this-repo> printgenie && cd printgenie/docker
cp .env.example .env && nano .env      # paste your Discord webhook URL
docker compose up -d
docker compose logs -f printguard
# open http://<pi-ip>:8000 → Add Camera (This device) → Add Printer (Camera Only) → Monitor
```

See `docker/.env.example` and `spikes/` for the rest.

---

## 🛡️ House rules baked in

- **Supabase DDL** → MCP `apply_migration`, **never** `supabase db push` (history-desync trap).
- **Secrets** → `.env` only, gitignored. Never commit keys.
- **Economy XP** → stable `source_id` so retries/replays bank exactly once (same pattern as the
  git-commit XP hooks).

---

## 🔗 Sources

- [oliverbravery/PrintGuard](https://github.com/oliverbravery/PrintGuard) · [v1.0.0b1 release](https://newreleases.io/project/github/oliverbravery/PrintGuard/release/v1.0.0b1)
- [Meshy API — AI Integration docs](https://docs.meshy.ai/en/api/ai) · [changelog](https://docs.meshy.ai/en/api/changelog)
- [Kobra X LAN Connection Guide](https://wiki.anycubic.com/en/fdm-3d-printer/anycubic-kobra-x/lan-connection-guide) · [Rinkhals (no Kobra X support)](https://github.com/jbatonnet/Rinkhals)
- [metheos/anycubic-s1-mqtt-bridge](https://github.com/metheos/anycubic-s1-mqtt-bridge) · [WaresWichall/hass-anycubic_cloud](https://github.com/WaresWichall/hass-anycubic_cloud)
