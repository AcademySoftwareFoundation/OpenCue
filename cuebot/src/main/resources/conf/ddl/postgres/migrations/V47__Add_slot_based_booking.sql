-- Slot-based booking: layers and hosts opt into concurrency-slot dispatch, where frames
-- book a whole-count slot instead of cores/memory.

-- Mark a layer as slot-based by requiring at least this many concurrency slots per frame.
-- 0 means the layer is not slot-based and books by cores/memory as usual.
alter table layer
    add int_slots_required INT DEFAULT 0 NOT NULL;

-- Limit the max number of concurrent frames a host may run (slot-based host).
-- -1 means the host is not slot-based and books by cores/memory as usual.
-- When >= 0 the host only runs slot-based layers, capped at this many concurrent slots.
alter table host
    add int_concurrent_slots_limit INT DEFAULT -1 NOT NULL;

-- Number of concurrency slots reserved by a proc (booked frame) on a slot-based host.
-- 0 for regular (cores/memory) procs. This is the single source of truth for slot
-- accounting: per-host and per subscription/folder/job slot usage both derive from
-- SUM(proc.int_slots_reserved).
alter table proc
    add int_slots_reserved INT DEFAULT 0 NOT NULL;

-- Per-hierarchy hard limit on concurrent slots for slot-based layers, parallel to the
-- cores/gpus limits. Enforced by the scheduler accounting store at subscription, folder
-- and job level. -1 means unlimited; 0 means reject all slot work; N caps at N slots.
-- Regular (cores/memory) layers are unaffected by this limit.
alter table subscription
    add int_max_slots INT DEFAULT -1 NOT NULL;

alter table folder_resource
    add int_max_slots INT DEFAULT -1 NOT NULL;

alter table job_resource
    add int_max_slots INT DEFAULT -1 NOT NULL;

-- Slot-based procs legitimately reserve 0 cores (they book by concurrency slots
-- instead), so relax the 0-core guard for them. At the same time make the database
-- the hard enforcement point for the per-host concurrent slots cap: the insert takes
-- a row lock on the host, which serializes slot bookings per host, then verifies
-- SUM(proc.int_slots_reserved) + NEW.int_slots_reserved stays within
-- host.int_concurrent_slots_limit. This also guarantees strict pairing on the host
-- side: a slot proc can only ever be inserted for a slot-based host.
CREATE OR REPLACE FUNCTION trigger__before_insert_proc()
RETURNS TRIGGER AS $body$
DECLARE
    slot_limit INT;
    slots_in_use INT;
BEGIN
    IF NEW.int_slots_reserved > 0 THEN
        SELECT int_concurrent_slots_limit INTO slot_limit FROM host
            WHERE pk_host = NEW.pk_host FOR UPDATE;
        IF slot_limit IS NULL OR slot_limit < 0 THEN
            RAISE EXCEPTION 'failed to allocate slots, host is not slot-based';
        END IF;
        SELECT COALESCE(SUM(int_slots_reserved), 0) INTO slots_in_use FROM proc
            WHERE pk_host = NEW.pk_host;
        IF slots_in_use + NEW.int_slots_reserved > slot_limit THEN
            RAISE EXCEPTION 'failed to allocate slots, host is at its concurrent slots limit';
        END IF;
    ELSIF NEW.int_cores_reserved <= 0 THEN
        RAISE EXCEPTION 'failed to allocate proc, tried to allocate 0 cores';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;
