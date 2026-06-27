# Contributing to Print Genie

Thanks for helping build an open, self-hosted print guardian for the Anycubic Kobra X (and beyond).
This is a small project — keep changes focused and the setup simple.

## Project shape

See [`README.md`](README.md) for the architecture and [`PROJECT_BOARD.md`](PROJECT_BOARD.md) for the
phase checklist. In short:

- **PrintGuard** (upstream Docker image) does the AI camera detection — we don't fork it.
- **`service/`** is a small FastAPI glue layer (webhook → Discord + Supabase + Meshy + economy).
- **`mcp/`** is an MCP server so Claude can query print status.
- **`spikes/`** is research + the Phase-4 cloud-pause adapter.

## Run it locally

```bash
# Glue service (Phase 2/3)
cd service
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in what you need; everything is optional/fail-soft
uvicorn app.main:app --reload --port 8011
# health check:
curl localhost:8011/health

# MCP server (Phase 3)
cd mcp && pip install -r requirements.txt
PRINTGENIE_URL=http://localhost:8011 python server.py
```

The full Pi deployment is in [`docs/PI_RUNBOOK.md`](docs/PI_RUNBOOK.md).

## The Phase-4 cloud-pause spike

See [`spikes/anycubic_cloud_pause.md`](spikes/anycubic_cloud_pause.md). It **reuses** the maintained
[`hass-anycubic_cloud`](https://github.com/WaresWichall/hass-anycubic_cloud) client — do **not**
reimplement the Anycubic app-signing. That client is **GPL**, so keep it a *runtime* dependency
(cloned + pointed at via `ANYCUBIC_CLOUD_API_PATH`); do not copy its source into this MIT-licensed repo.

## House rules

- **Secrets live in `.env` only** (gitignored). Never commit a key, token, or webhook URL. Only
  `.env.example` files (with blank values) belong in git.
- **Supabase DDL** goes through the Supabase MCP `apply_migration` tool, **never** `supabase db push`.
- **Dependencies:** the service deliberately uses `httpx` + stdlib (`os.getenv`) — no `supabase` SDK,
  no `pydantic-settings`. Don't add a dependency unless code actually imports it.
- **Fail-soft:** alerting/logging must never crash the webhook path. Wrap side-effects in try/except.
- **Auto-pause is pause-only** and off by default. Never auto-*cancel* (destructive).

## Pull requests

1. Keep PRs small and scoped to one thing.
2. Make sure it compiles and tests pass: `python -m py_compile service/app/*.py mcp/server.py` and
   `pytest` (see `tests/`). CI runs both on every push.
3. Update `PROJECT_BOARD.md` checkboxes / `README.md` if your change affects a phase.
4. Describe what you tested (especially anything touching real hardware or the cloud).
