-- HELM — complaint follow-up-call fields.
-- Adds the columns that back the "☎ Client needs a follow-up call" feature.
-- Run ONCE in the Supabase SQL editor (Dashboard → SQL Editor → New query → Run).
-- Idempotent + additive (nullable / default false), so it's safe to run before
-- or after the app deploy — existing complaints are untouched.

alter table public.complaints
  add column if not exists needs_callback boolean not null default false,
  add column if not exists callback_phone text,
  add column if not exists callback_note  text;

-- The follow-up call is its own task, tracked independently of whether the
-- complaint is resolved (the call is usually made AFTER the complaint closes).
-- These back the "☎ Needs Callback" stat card + the "✓ Mark call made" button.
alter table public.complaints
  add column if not exists callback_done    boolean not null default false,
  add column if not exists callback_done_at timestamptz,
  add column if not exists callback_done_by text;

-- No RLS changes needed: the new columns inherit the complaints table's existing
-- policies (authenticated insert/select), which already cover reps logging a
-- complaint and the console reading it.
