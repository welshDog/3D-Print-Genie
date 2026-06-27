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
| **`service/app/pause.py` is a no-op stub** | Fill it in only after Phase-4 spike confirms the cloud MQTT schema |
| **XP `source_id=print:<job_id>`** must be stable | Retries/replays must bank exactly once (same pattern as git-commit XP hooks) |
| **Alert path must never crash** | Supabase writes are fail-soft — a DB blip must never silence a Discord alert |

---

## Phase 4 — closed-loop pause spike

The most wanted feature. See **`spikes/anycubic_cloud_pause.md`** for the full research.
Short version:

1. Stand up `WaresWichall/hass-anycubic_cloud` against your real account.
2. Confirm the Kobra X appears and capture its `printer_id`.
3. Subscribe to the cloud status topic (read-only, zero risk).
4. Test a `pause` command on a throwaway print.
5. If step 4 works: fill in `service/app/pause.py:try_cloud_pause()` and open a PR.
6. If it doesn't: document what you found and open an issue — that evidence is still valuable.

**Do not ship auto-pause without step 4 being reproducible on the Kobra X.**

---

## Opening a PR

- One concern per PR — small and reviewable.
- If adding a new printer integration (Bambu, Prusa, etc.), add a section to `docs/PI_RUNBOOK.md`.
- If changing the DB schema, add a new migration file (`0002_...sql`) — never edit existing ones.
- Run `python -m py_compile service/app/*.py mcp/server.py` before pushing — catches import errors.

---

## Getting help

Open a GitHub issue or find WelshDog in the **Hyperfocus Zone Discord**.
