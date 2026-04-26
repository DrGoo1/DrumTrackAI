-- Supabase calibration core: roles, mapping, audit, jobs with RLS
create extension if not exists pgcrypto;

create table if not exists public.app_user_roles (
  user_id uuid not null,
  role text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, role)
);

create table if not exists public.user_drummer_map (
  user_id uuid not null,
  drummer_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, drummer_id)
);

create table if not exists public.calibration_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid,
  drummer_id text,
  run_id text,
  action text not null,
  payload jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  drummer_id text not null,
  status text not null,
  input_json jsonb,
  result_json jsonb,
  error_text text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Indexes
create index if not exists idx_user_drummer_map_user on public.user_drummer_map(user_id);
create index if not exists idx_user_drummer_map_drummer on public.user_drummer_map(drummer_id);
create index if not exists idx_analysis_jobs_drummer_time on public.analysis_jobs(drummer_id, created_at);

-- RLS policies
alter table public.app_user_roles enable row level security;
alter table public.user_drummer_map enable row level security;
alter table public.calibration_audit_log enable row level security;
alter table public.analysis_jobs enable row level security;

-- app_user_roles: users can read their own roles; service role full access
create policy if not exists app_user_roles_read_own
  on public.app_user_roles for select
  to authenticated
  using (user_id = auth.uid());

create policy if not exists app_user_roles_all_service
  on public.app_user_roles for all
  to service_role
  using (true)
  with check (true);

-- user_drummer_map: users can read their own mappings; service role full access
create policy if not exists user_drummer_map_read_own
  on public.user_drummer_map for select
  to authenticated
  using (user_id = auth.uid());

create policy if not exists user_drummer_map_all_service
  on public.user_drummer_map for all
  to service_role
  using (true)
  with check (true);

-- calibration_audit_log: users can select their own rows; service role full access
create policy if not exists calibration_audit_log_read_own
  on public.calibration_audit_log for select
  to authenticated
  using (actor_user_id = auth.uid());

create policy if not exists calibration_audit_log_all_service
  on public.calibration_audit_log for all
  to service_role
  using (true)
  with check (true);

-- analysis_jobs: users can read jobs for drummers they have mapping for; service role full access
create policy if not exists analysis_jobs_read_by_mapping
  on public.analysis_jobs for select
  to authenticated
  using (
    exists (
      select 1
      from public.user_drummer_map m
      where m.user_id = auth.uid()
        and m.drummer_id = analysis_jobs.drummer_id
    )
  );

create policy if not exists analysis_jobs_all_service
  on public.analysis_jobs for all
  to service_role
  using (true)
  with check (true);
