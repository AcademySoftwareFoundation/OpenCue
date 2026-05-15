-- Adds ts_available timestamp columns to the frame, layer, and job tables.
-- These track when an object became eligible to run -- i.e. when it transitioned
-- out of a dependency state (DEPEND -> WAITING) or, for objects that were
-- never blocked, when the object was created (effectively the job's
-- submission time).
--
-- The pycue/Cuebot wrappers expose this through `Frame.availableTime()`,
-- `Layer.availableTime()` and `Job.availableTime()`.

-- frame.ts_available is NULL for frames still in DEPEND -- they have no
-- available time until their dependencies clear.
ALTER TABLE frame
    ADD COLUMN ts_available TIMESTAMP (6) WITH TIME ZONE DEFAULT NULL;

-- Backfill ts_available for existing frames that have already left DEPEND. We
-- don't know the exact moment they unblocked, so fall back to the job's
-- submission time. Frames still in DEPEND keep ts_available NULL until the
-- trigger fires.
UPDATE frame f
SET ts_available = j.ts_started
FROM job j
WHERE f.pk_job = j.pk_job
  AND f.ts_available IS NULL
  AND f.str_state <> 'DEPEND';

-- layer.ts_available defaults to layer creation time. Layers aren't blocked
-- by a dependency-state machine of their own, so this value approximates the
-- time the layer became eligible.
ALTER TABLE layer
    ADD COLUMN ts_available TIMESTAMP (6) WITH TIME ZONE;

UPDATE layer l
SET ts_available = j.ts_started
FROM job j
WHERE l.pk_job = j.pk_job
  AND l.ts_available IS NULL;

ALTER TABLE layer
    ALTER COLUMN ts_available SET DEFAULT current_timestamp,
    ALTER COLUMN ts_available SET NOT NULL;

-- job.ts_available mirrors ts_started for existing jobs (job.ts_started
-- already captures submission time). Going forward new jobs will pick up
-- current_timestamp via the column default.
ALTER TABLE job
    ADD COLUMN ts_available TIMESTAMP (6) WITH TIME ZONE;

UPDATE job
SET ts_available = ts_started
WHERE ts_available IS NULL;

ALTER TABLE job
    ALTER COLUMN ts_available SET DEFAULT current_timestamp,
    ALTER COLUMN ts_available SET NOT NULL;

-- Re-create the DEPEND -> WAITING trigger so it also stamps ts_available.
CREATE OR REPLACE FUNCTION trigger__update_frame_dep_to_wait()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'WAITING';
    NEW.ts_updated := current_timestamp;
    NEW.ts_available := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

-- Stamp ts_available when a frame is inserted directly in WAITING (no dependency).
CREATE OR REPLACE FUNCTION trigger__set_frame_ts_available_on_insert()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.str_state = 'WAITING' AND NEW.ts_available IS NULL THEN
        NEW.ts_available := current_timestamp;
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER set_frame_ts_available_on_insert BEFORE INSERT ON frame
FOR EACH ROW
EXECUTE PROCEDURE trigger__set_frame_ts_available_on_insert();
