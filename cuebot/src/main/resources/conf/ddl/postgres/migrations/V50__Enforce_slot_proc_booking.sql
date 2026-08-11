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
