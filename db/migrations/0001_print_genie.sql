-- Print Genie — Phase 2 schema: print_jobs + print_events
--
-- HOUSE RULE: apply this via the Supabase MCP `apply_migration` tool, NEVER `supabase db push`
-- (history-desync trap noted across HyperCore). Owner-only RLS; the glue service uses the
-- service-role key (which bypasses RLS) to write.
--
-- Lives in its own schema to keep it cleanly separated from other HyperCore projects.

create schema if not exists print_genie;

-- One row per print attempt.
create table if not exists print_genie.print_jobs (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    started_at      timestamptz,
    ended_at        timestamptz,
    model           text not null,
    filament        text,
    profile         text,
    duration_mins   integer,
    result          text not null default 'running'
                    check (result in ('running', 'success', 'failure', 'paused', 'cancelled')),
    failure_type    text,                 -- 'spaghetti' | 'adhesion' | 'warp' | 'blob' | ...
    snapshot_url    text,                 -- last camera frame on failure
    -- Meshy preflight verdict (Phase 2), null until checked.
    preflight_passed    boolean,
    preflight_report    jsonb,
    notes           text,
    owner_discord_id    text not null default '418075243404591106'
);

-- Append-only spine of detection events from PrintGuard (one job → many events).
create table if not exists print_genie.print_events (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    job_id          uuid references print_genie.print_jobs(id) on delete set null,
    event_type      text not null,        -- 'detection' | 'pause' | 'resume' | 'start' | 'finish'
    score           numeric,              -- PrintGuard confidence for the frame
    failure_type    text,
    snapshot_url    text,
    raw             jsonb                 -- full PrintGuard webhook payload, for forensics
);

create index if not exists print_jobs_created_at_idx on print_genie.print_jobs (created_at desc);
create index if not exists print_jobs_result_idx     on print_genie.print_jobs (result);
create index if not exists print_events_job_id_idx    on print_genie.print_events (job_id);
create index if not exists print_events_created_at_idx on print_genie.print_events (created_at desc);

-- RLS: lock down to backend (service-role bypasses RLS); no anon/authenticated access by default.
alter table print_genie.print_jobs   enable row level security;
alter table print_genie.print_events enable row level security;

-- Intentionally NO permissive policies for anon/authenticated — all access is via service-role.
-- Add a per-user policy here later if a client UI is built.
