# Contributing to Print Genie 🧞

Thanks for wanting to help solve dodgy prints for everyone. This doc covers how to run the
project locally, the house rules, and how to contribute — whether that's a bug fix, a new
printer integration, or a Phase-4 cloud-pause breakthrough.

---

## Who this project is for

Anyone with a **filament 3D printer** who's tired of wasted spools and failed jobs. The first
target is the **Anycubic Kobra X** (closed firmware, camera-only AI detection), but the glue
service and MCP server work with any printer PrintGuard supports.

---

## Quick local dev setup

### Prerequisites
- Python 3.11+
- Docker + Docker Compose plugin
- A webcam or IP camera
- A Discord webhook URL (free — any server you own)

### 1. Clone + env files
```bash
git clone https://github.com/welshDog/3D-Print-Genie.git
cd 3D-Print-Genie

# Glue service
cp service/.env.example service/.env
# Fill in at minimum: DISCORD_WEBHOOK_URL and PRINTGENIE_WEBHOOK_SECRET

# Docker (PrintGuard on Pi)
cp docker/.env.example docker/.env
```

### 2. Run PrintGuard (Phase 1)
```bash
cd docker
docker compose up -d
# Open http://localhost:8000 → add camera → add printer (Camera Only) → add monitor
```

### 3. Run the glue service (Phase 2/3)
```bash
cd service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8011
# Health check: curl http://localhost:8011/health
```

### 4. Run the MCP server (Phase 3)
```bash
cd mcp
pip install -r requirements.txt
export PRINTGENIE_URL=http://localhost:8011
python server.py
# Point Claude Code / Claude Desktop at this with stdio transport
```

### 5. Apply the DB migration (Phase 2, Supabase)
```
# Use the Supabase MCP apply_migration tool — NEVER supabase db push
# This avoids the migration history desync trap documented in the README.
SQL file: db/migrations/0001_print_genie.sql
```

---

## House rules

| Rule | Why |
|------|-----|
| **Secrets in `.env` only** — never commit keys | `.env` is gitignored; `.env.example` is safe |
| **DB changes via MCP `apply_migration`** | `supabase db push` desyncs migration history |
| **Auto-pause stays `AUTO_PAUSE_ENABLED=false`** until the Kobra X spike is proven | Camera-only cannot pause the X — see `spikes/anycubic_cloud_pause.md` |
| **`service/app/pause.py` is implemented but OFF by default** | Real `try_cloud_pause` (cooldown-gated, pause-only); only fires when `AUTO_PAUSE_ENABLED=true` and creds are set |
| **XP `source_id=print:<job_id>`** must be stable | Retries/replays must bank exactly once (same pattern as git-commit XP hooks) |
| **Alert path must never crash** | Supabase writes are fail-soft — a DB blip must never silence a Discord alert |

---

## Phase 4 — closed-loop pause (schema mapped, hardware-test pending)

The most wanted feature. The schema is already **mapped and coded** — see
**`spikes/anycubic_cloud_pause.md`** for the full research. Key facts:

- Pause is a **REST call**: `POST /work/operation/sendOrder` with `{"order_id": 2, "printer_id", "project_id"}` — **not** raw MQTT.
- We **reuse** the maintained `WaresWichall/hass-anycubic_cloud` client (`pause_print`) — do **not** reimplement the Anycubic app-signing. That client is **GPL**, so keep it a *runtime* dependency (cloned + `ANYCUBIC_CLOUD_API_PATH`), never copied into this MIT repo.
- `service/app/pause.py::try_cloud_pause()` is **already implemented** (off by default, cooldown-gated, pause-only).

What's left is to **verify on a real Kobra X** (it may differ from its proven sibling, the Kobra S1):

1. Clone `hass-anycubic_cloud`; capture a one-time access token.
2. Run `python spikes/probe_anycubic.py` (read-only) → confirm the Kobra X appears, copy its `printer_id`.
3. Run `python spikes/probe_anycubic.py --pause` on a throwaway print → confirm it pauses on the panel.
4. If step 3 works: set `ANYCUBIC_*` + `AUTO_PAUSE_ENABLED=true` and open a PR with what you tested.
5. If it doesn't: document the delta in the spike doc and open an issue — that evidence is still valuable.

**Do not enable auto-pause without step 3 being reproducible on the Kobra X.**

---

## Opening a PR

- One concern per PR — small and reviewable.
- If adding a new printer integration (Bambu, Prusa, etc.), add a section to `docs/PI_RUNBOOK.md`.
- If changing the DB schema, add a new migration file (`0002_...sql`) — never edit existing ones.
- Run `python -m py_compile service/app/*.py mcp/server.py` before pushing — catches import errors.

---

## Getting help

Open a GitHub issue or find WelshDog in the **Hyperfocus Zone Discord**.
