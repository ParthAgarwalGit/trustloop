-- TrustLoop data sink: Supabase (Postgres) schema.
--
-- Run this once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
--
-- SECURITY MODEL
-- The app is a static site, so its anon key ships inside the JavaScript bundle and
-- must be treated as public. The policies below therefore grant the anonymous role
-- INSERT and nothing else: a stranger who extracts the key can add junk rows but
-- cannot read, alter or delete anyone's data. You read the table through the
-- dashboard or a service-role key that never leaves your machine.

create table if not exists public.sessions (
  id            bigint generated always as identity primary key,
  inserted_at   timestamptz not null default now(),
  participant_id text        not null,
  prolific_pid  text,
  disclosure    text        not null check (disclosure in ('opaque','full')),
  tone          text        not null check (tone in ('honest','sycophantic')),
  is_preview    boolean     not null default false,
  app_version   text,
  completed_at  timestamptz,
  data          jsonb       not null
);

create index if not exists sessions_participant_idx on public.sessions (participant_id);
create index if not exists sessions_cell_idx        on public.sessions (disclosure, tone);

alter table public.sessions enable row level security;

-- Anonymous participants may submit, and may do nothing else.
drop policy if exists "anon can insert sessions" on public.sessions;
create policy "anon can insert sessions"
  on public.sessions for insert
  to anon
  with check (true);

-- No SELECT / UPDATE / DELETE policy is defined for `anon`, so with RLS enabled all
-- three are denied by default. Do not add one.


-- ---------------------------------------------------------------------------
-- Monitoring while the study runs. Run in the SQL editor as needed.
-- ---------------------------------------------------------------------------

-- Live cell counts (completed, non-preview sessions only):
--
--   select disclosure, tone, count(*) as n
--   from public.sessions
--   where completed_at is not null and not is_preview
--   group by disclosure, tone
--   order by disclosure, tone;

-- Duplicate submissions from one participant (Prolific returns + retakes):
--
--   select participant_id, count(*)
--   from public.sessions
--   group by participant_id having count(*) > 1;

-- Participants who withdrew at debrief (exclude these from analysis):
--
--   select participant_id
--   from public.sessions
--   where (data -> 'survey' ->> 'withdrawn') = '1';


-- ---------------------------------------------------------------------------
-- Export for analysis
-- ---------------------------------------------------------------------------
-- Dashboard route: Table Editor -> sessions -> Export -> CSV. Then split into the
-- per-session JSON files prepare_data.py expects:
--
--   python analysis/export_supabase.py --csv sessions_rows.csv --out data/raw
--
-- Or pull directly with the service-role key (keep it in your shell, not in a file):
--
--   curl "$SUPABASE_URL/rest/v1/sessions?select=data&completed_at=not.is.null" \
--     -H "apikey: $SUPABASE_SERVICE_KEY" \
--     -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" > sessions.json
