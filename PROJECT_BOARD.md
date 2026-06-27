# 📋 Print Genie — Project Board

Phase checklist + status for the Kobra X Print Guardian. Tick boxes as you go.

**Legend:** ✅ done · 🔨 scaffolded (code ready, needs hardware/creds) · 🅿️ parked · ⬜ todo

---

## 🗂️ Board at a glance

| Phase | Status | One-liner |
|------|--------|-----------|
| 0 — Physical + browser demo | ⬜ todo (needs Pi/printer) | Tune printer, mount cam, LAN Mode on, browser sanity-check |
| 1 — Detection + Discord alert | 🔨 scaffolded | PrintGuard on Pi → spaghetti alert on phone |
| 2 — Supabase log + Meshy preflight | 🔨 scaffolded | Job log + STL printability check |
| 3 — MCP + BROski economy | 🔨 scaffolded | "How's my print going?" + XP per success |
| 4 — Closed-loop auto-pause | 🅿️ parked (schema mapped) | Pause the X via Anycubic cloud |

---

## Phase 0 — Physical + browser demo  ⬜
*No code. Do this first when hardware lands.*

- [ ] Kobra X tune-up: wash plate, belt tension, eccentric nuts, lube rails
- [ ] Run first-layer calibration
- [ ] Mount USB webcam to top frame bar (whole bed in frame)
- [ ] Enable **LAN Mode** (Settings → Network → LAN Mode)
- [ ] Sanity-check detection in-browser at oliverbravery.github.io/PrintGuard

## Phase 1 — Detection + Discord alert  🔨
*Code ready: `docker/docker-compose.yml`, `docs/PI_RUNBOOK.md`.*

- [x] Write Pi/Linux PrintGuard `docker-compose.yml`
- [x] Write copy-paste Pi runbook
- [ ] Flash Pi OS Lite 64-bit + install Docker
- [ ] `docker compose up -d` → dashboard loads at `:8000`
- [ ] Add camera → Camera-Only printer "Kobra X" → Monitor
- [ ] Set thresholds: sensitivity 0.7, 10–15 sustained frames, **Notify only**
- [ ] Wire Discord webhook + Test
- [ ] ✅ Acceptance: deliberate spaghetti → Discord alert + snapshot in seconds

## Phase 2 — Supabase log + Meshy preflight  🔨
*Code ready: `db/migrations/0001_print_genie.sql`, `service/app/{main,supabase_client,meshy}.py`.*

- [x] Write `print_jobs` / `print_events` migration (RLS owner-only)
- [x] Build FastAPI webhook receiver + Supabase writer
- [x] Build corrected **async** Meshy preflight client
- [ ] Apply migration via Supabase MCP `apply_migration` (NOT `db push`)
- [ ] Fill `SUPABASE_*` + `MESHY_API_KEY` in `.env`
- [ ] `docker compose --profile glue up -d`
- [ ] ✅ Acceptance: finished print → `print_jobs` row; broken STL → non-manifold flagged

## Phase 3 — MCP + BROski economy  🔨
*Code ready: `mcp/server.py`, `service/app/economy.py`.*

- [x] Build MCP server (`print_status`, `recent_jobs`, `job_stats`)
- [x] Build economy XP caller (`source_id=print:<job_id>` dedup)
- [ ] Point MCP client at the glue service (`PRINTGENIE_URL`)
- [ ] ✅ Acceptance: ask Claude "how's my print going?" → live status + snapshot
- [ ] ✅ Acceptance: `success` event banks XP exactly once (dedup holds on replay)

## Phase 4 — Closed-loop auto-pause  🅿️
*Schema mapped + coded. Parked until the Pi arrives. See `spikes/anycubic_cloud_pause.md`.*

- [x] Map pause path (REST `sendOrder` order_id=2; hosts/auth/order-IDs)
- [x] Decide: reuse `anycubic_cloud_api`, don't reimplement signing
- [x] Build read-only discovery probe (`spikes/probe_anycubic.py`)
- [x] Build real `try_cloud_pause` adapter (off by default, cooldown, pause-only)
- [ ] Clone `hass-anycubic_cloud`; get a one-time access token
- [ ] Run probe → confirm Kobra X appears, copy its `printer_id` (read-only)
- [ ] Throwaway-print `--pause` test → printer pauses on the panel
- [ ] If S1 schema matches: set `AUTO_PAUSE_ENABLED=true`
- [ ] Decision gate: ship auto-pause, or document "not feasible on X" + stay alert-only

---

## 🧱 Want a native GitHub Projects board?

This file is the source of truth, but if you'd like a drag-and-drop kanban on GitHub, grant the scope
once and tell me — I'll create the board and seed it with one issue per phase:

```bash
gh auth refresh -s project,read:project   # run this yourself (interactive)
```

Then say *"make the native board"* and I'll build it.
