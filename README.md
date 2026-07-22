# 🧞 3D Print Genie

> 🟢 ACTIVE — Part of the [WelshDog Toolbox](https://github.com/welshDog/HyperFocus-Zone-Portal#-everyday-toolbox) | [HyperFocus Zone](https://github.com/welshDog/HyperFocus-Zone-Portal)

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Built in Wales](https://img.shields.io/badge/Built%20in-Wales%20🏴-red)](https://github.com/welshDog)

> *HyperCore-native AI Print Guardian for the Anycubic Kobra X*
> STL → preflight → print → AI camera watch → **Discord alert** → **Supabase** job log → queryable by **Claude (MCP)** → **BROski XP** on success

---

## 🥔 Who this is for

**You, if any of these are true:**
- You have a 3D printer (especially an Anycubic Kobra X) and hate babysitting it for spaghetti failures
- You want AI to watch your print via webcam and ping you on Discord if something goes wrong
- You want your printer jobs logged in Supabase so Claude/agents can answer *"how’s my print going?"*
- You want to earn BROski XP when a print finishes successfully 💪

Built specifically around the **Kobra X**’s locked-down architecture (no OctoPrint/Moonraker), using camera-only AI failure detection.

---

## ⚡ One-Command Run (Phase 1 — Detection + Discord Alert)

```bash
# On Raspberry Pi 4/5 with Docker installed:
git clone https://github.com/welshDog/3D-Print-Genie.git printgenie
cd printgenie/docker
cp .env.example .env
nano .env  # Add your Discord webhook URL
docker compose up -d

# Then open the PrintGuard UI:
# http://<your-pi-ip>:8000
# → Add Camera (This device) → Add Printer (Camera Only) → Monitor
```

**Test the full pipeline with NO hardware:**
```bash
# Terminal 1 — start the glue service
cd service && python -m uvicorn app.main:app --port 8011 --env-file .env

# Terminal 2 — run the fake printer simulator
python tools/simulate_printguard.py scenario
# Proves: webhook auth → event log → Discord alert → finish → BROski XP
```

---

## 🖥️ What you see when it works

- ✅ PrintGuard UI running at `http://<pi-ip>:8000` — live camera feed with AI confidence score
- 💬 Discord message in your `#print-genie` channel: `⚠️ Failure detected! Confidence: 87% — [snapshot attached]`
- 📊 Supabase: new row in `print_events` table with timestamp, score, and job ID
- 🏆 BROski XP awarded to your wallet when a job completes successfully
- 🤖 Claude can answer: *"Print Genie: what’s my last job status?"* via MCP

---

## 🏗️ Architecture

```
Kobra X (LAN Mode)           Raspberry Pi 4/5              HyperCore stack
  USB webcam ───────────▶  PrintGuard (Docker :8000)    ├─ Discord (alerts)
                             AI scores every frame         ├─ Supabase (job log)
                                  │ webhook on failure    ├─ MCP server (Claude)
                                  ▼                       └─ BROski XP per success
                             Print Genie (FastAPI glue)
```

---

## 🚦 Build Phases

| Phase | What it adds | Status |
|---|---|---|
| 0 — Physical setup | Calibrate printer, mount webcam, enable LAN Mode | ✅ Done |
| 1 — Detection + Discord | Camera AI → webhook → Discord alert | ✅ Done |
| 2 — Supabase job log | FastAPI writes `print_events` + `print_jobs` + Meshy preflight | ✅ Done |
| 3 — MCP + BROski XP | Claude can query status; XP awarded on success | ✅ Done |
| 4 — Auto-pause | Closed-loop pause via Anycubic Cloud MQTT | 🔧 Spike done, opt-in |

---

## 🔗 How it connects to Hyperfocus Zone

| Connection | Detail |
|---|---|
| 💜 Supabase | Print jobs logged to your HyperFocus Zone Supabase backend |
| 🤖 MCP | MCP server lets Claude answer print status questions |
| 💎 BROski XP | Successful prints award XP via HyperCode-V2.4 economy API |
| 💬 Discord | Alerts sent to your BROski community Discord server |
| 🏠 Ecosystem | Part of the WelshDog Toolbox — [HyperFocus Zone Portal](https://github.com/welshDog/HyperFocus-Zone-Portal) |

---

## 🧪 Tests

```bash
pytest -q  # 33 no-network tests (auth, XP dedup, Meshy flow, pause rails)
```

---

## 📖 Full Docs

- [`docs/PI_RUNBOOK.md`](docs/PI_RUNBOOK.md) — Blank SD card → Discord spaghetti alert walkthrough
- [`PROJECT_BOARD.md`](PROJECT_BOARD.md) — Live phase checklist
- [`spikes/anycubic_cloud_pause.md`](spikes/anycubic_cloud_pause.md) — Phase 4 auto-pause research

---

<div align="center">

**Part of the WelshDog Toolbox — Built with 🧠 + ❤️ in Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥**

*by [@welshDog](https://github.com/welshDog) — Lyndz Williams*

[🊪 Back to HyperFocus Zone Portal](https://github.com/welshDog/HyperFocus-Zone-Portal) · [💙 Sponsor](https://github.com/sponsors/welshDog) · [🛒 Shop](https://welshdog.shop)

</div>
