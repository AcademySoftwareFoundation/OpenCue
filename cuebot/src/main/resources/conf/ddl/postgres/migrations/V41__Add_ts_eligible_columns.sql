-- Adds ts_eligible timestamp columns to the frame, layer, and job tables.
-- These track when an object became eligible to run -- i.e. when it transitioned
-- out of a dependency state (DEPEND -> WAITING) or, for objects that were
-- never blocked, when the object was created (effectively the job's
-- submission time).
--
-- The pycue/Cuebot wrappers expose this through `Frame.eligibleTime()`,
-- `Layer.eligibleTime()` and `Job.eligibleTime()`.

-- frame.ts_eligible is NULL for frames still in DEPEND -- they have no
-- eligible time until their dependencies clear.
ALTER TABLE frame
    ADD COLUMN ts_eligible TIMESTAMP (6) WITH TIME ZONE DEFAULT NULL;

-- Backfill ts_eligible for existing frames that have already left DEPEND. We
-- don't know the exact moment they unblocked, so fall back to the job's
-- submission time. Frames still in DEPEND keep ts_eligible NULL until the
-- trigger fires.
UPDATE frame f
SET ts_eligible = j.ts_started
FROM job j
WHERE f.pk_job = j.pk_job
  AND f.ts_eligible IS NULL
  AND f.str_state <> 'DEPEND';

-- layer.ts_eligible defaults to layer creation time. Layers aren't blocked
-- by a dependency-state machine of their own, so this value approximates the
-- time the layer became eligible.
ALTER TABLE layer
    ADD COLUMN ts_eligible TIMESTAMP (6) WITH TIME ZONE;

UPDATE layer l
SET ts_eligible = j.ts_started
FROM job j
WHERE l.pk_job = j.pk_job
  AND l.ts_eligible IS NULL;

ALTER TABLE layer
    ALTER COLUMN ts_eligible SET DEFAULT current_timestamp,
    ALTER COLUMN ts_eligible SET NOT NULL;

-- job.ts_eligible mirrors ts_started for existing jobs (job.ts_started
-- already captures submission time). Going forward new jobs will pick up
-- current_timestamp via the column default.
ALTER TABLE job
    ADD COLUMN ts_eligible TIMESTAMP (6) WITH TIME ZONE;

UPDATE job
SET ts_eligible = ts_started
WHERE ts_eligible IS NULL;

ALTER TABLE job
    ALTER COLUMN ts_eligible SET DEFAULT current_timestamp,
    ALTER COLUMN ts_eligible SET NOT NULL;

-- Re-create the DEPEND -> WAITING trigger so it also stamps ts_eligible.
CREATE OR REPLACE FUNCTION trigger__update_frame_dep_to_wait()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'WAITING';
    NEW.ts_updated := current_timestamp;
    NEW.ts_eligible := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

-- Stamp ts_eligible when a frame is inserted directly in WAITING (no dependency).
CREATE OR REPLACE FUNCTION trigger__set_frame_ts_eligible_on_insert()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.str_state = 'WAITING' AND NEW.ts_eligible IS NULL THEN
        NEW.ts_eligible := current_timestamp;
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER set_frame_ts_eligible_on_insert BEFORE INSERT ON frame
FOR EACH ROW
EXECUTE PROCEDURE trigger__set_frame_ts_eligible_on_insert();
