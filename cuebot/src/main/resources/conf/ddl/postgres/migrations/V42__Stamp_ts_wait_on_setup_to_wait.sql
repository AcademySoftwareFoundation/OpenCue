-- V41 added a BEFORE INSERT trigger to stamp frame.ts_wait when frames are
-- inserted directly in WAITING. In practice Cuebot always inserts frames in
-- SETUP and bulk-transitions them to WAITING from JobManagerService.activateJob,
-- so the BEFORE INSERT trigger never fires. This migration adds a BEFORE
-- UPDATE trigger that stamps ts_wait when frames first move SETUP -> WAITING,
-- and backfills any frames that already made the jump before this migration.

CREATE OR REPLACE FUNCTION trigger__set_frame_ts_wait_setup_to_wait()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.ts_wait := current_timestamp;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER set_frame_ts_wait_setup_to_wait BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (OLD.str_state = 'SETUP' AND NEW.str_state = 'WAITING')
  EXECUTE PROCEDURE trigger__set_frame_ts_wait_setup_to_wait();

-- Backfill ts_wait for frames that have already left SETUP but never got a
-- stamp (because they activated before this migration ran). We don't know the
-- precise activation time, so fall back to the job's submission time. Frames
-- still in SETUP or DEPEND legitimately keep ts_wait NULL until they unblock.
UPDATE frame f
SET ts_wait = j.ts_started
FROM job j
WHERE f.pk_job = j.pk_job
  AND f.ts_wait IS NULL
  AND f.str_state <> 'SETUP'
  AND f.str_state <> 'DEPEND';
