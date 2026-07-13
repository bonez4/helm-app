-- HELM — complaint follow-up-call fields.
-- Adds the columns that back the "☎ Client needs a follow-up call" feature.
-- Run ONCE in the Supabase SQL editor (Dashboard → SQL Editor → New query → Run).
-- Idempotent + additive (nullable / default false), so it's safe to run before
-- or after the app deploy — existing complaints are untouched.

alter table public.complaints
  add column if not exists needs_callback boolean not null default false,
  add column if not exists callback_phone text,
  add column if not exists callback_note  text;

-- No RLS changes needed: the new columns inherit the complaints table's existing
-- policies (authenticated insert/select), which already cover reps logging a
-- complaint and the console reading it.
