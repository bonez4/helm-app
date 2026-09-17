-- HELM — edit-tracking columns for client notes.
-- Backs the ✎ Edit button on a client card's Notes history: when a note is
-- edited in place, the app stamps who/when here and shows a small "edited"
-- marker on the row. Run ONCE in the Supabase SQL editor.
-- Idempotent + additive (nullable), so existing notes and every report that
-- reads the notes table are untouched. The app degrades gracefully until this
-- is run: an edit still saves the note text/action/date, it just isn't marked.

alter table public.notes
  add column if not exists edited_at timestamptz,
  add column if not exists edited_by text;

-- No RLS changes needed: notes already allows authenticated UPDATE/DELETE
-- (the × delete button has always used it); the new columns inherit that.
