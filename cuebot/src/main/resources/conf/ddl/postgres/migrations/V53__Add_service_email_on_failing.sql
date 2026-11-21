-- Opt-in per service (and per show override): email the job's owner when a job stops running
-- with dead frames on a layer whose service has this on.
--
-- Additive: the columns are nullable, or NOT NULL with a constant default, so no table is
-- rewritten and an older Cuebot keeps working against a migrated database.

ALTER TABLE service ADD COLUMN IF NOT EXISTS b_email_on_failing BOOLEAN DEFAULT false NOT NULL;
ALTER TABLE show_service ADD COLUMN IF NOT EXISTS b_email_on_failing BOOLEAN DEFAULT false NOT NULL;

-- The latest frame start of the job run the failing job email was sent for. Every run starts
-- frames, so a later start is a new run: the email goes out once per run, however many frame
-- completions or Cuebots see the job stop.
ALTER TABLE job ADD COLUMN IF NOT EXISTS ts_failing_email TIMESTAMP (6) WITH TIME ZONE;
