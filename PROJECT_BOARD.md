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
| 2.5 — Hardware-free E2E harness | ✅ done (2026-07-02) | Fake printer + 33 tests prove the glue loop with no hardware |
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
- [x] Apply migration to **jnrk** (Hyperfocus-Home-Page project) — done 2026-07-02 via
      `supabase db query --linked` (MCP token is tlav-scoped now; `db query` also avoids
      polluting the shop repo's migration history). Verified: RLS on, service_role granted,
      anon locked out, FK smoke insert/delete green.
- [x] `print_genie` added to jnrk API **Exposed schemas** — done 2026-07-02 via Management API
      PATCH (dashboard save had landed on the wrong project; verified anon=42501 denied,
      service_role=200)
- [x] `SUPABASE_*` (jnrk) filled in `service/.env` (gitignored) — `MESHY_API_KEY` still todo
- [x] ✅ **LIVE E2E against jnrk 2026-07-02**: simulator detection → real `print_events` row
      (FK'd to job) → finish → `print_jobs.result=success`. Test rows cleaned after proof.
- [ ] On the Pi: `docker compose --profile glue up -d` (copy the same .env)
- [ ] ✅ Acceptance (needs Meshy key): broken STL → non-manifold flagged

## Phase 2.5 — Hardware-free E2E harness  ✅ (2026-07-02)
*Everything provable before the Pi arrives is now proven. `tools/simulate_printguard.py` + `tests/`.*

- [x] Fake printer CLI: detection (both payload variants), finish, preflight, full scenario
- [x] Secret auth extended to **all** mutating endpoints (`/jobs/{id}/finish`, `/preflight` were open)
- [x] `/status` made genuinely fail-soft (Supabase outage no longer 500s the MCP path)
- [x] `config.py` reads env at init (testable via monkeypatch + `get_settings.cache_clear()`)
- [x] Test suite 5 → 33: auth, webhook parsing variants, XP dedup wiring, economy payload,
      Meshy create→poll→timeout flow, pause safety rails, MCP `job_stats` rollup
- [x] Live local run verified: uvicorn on :8011 + simulator scenario → all 200s, bad secret → 401

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
