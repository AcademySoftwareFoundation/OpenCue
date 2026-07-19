-- Number of concurrency slots reserved by a proc (booked frame) on a slot-based host.
-- 0 for regular (cores/memory) procs. This is the single source of truth for slot
-- accounting: per-host and per subscription/folder/job slot usage both derive from
-- SUM(proc.int_slots_reserved).
alter table proc
    add int_slots_reserved INT DEFAULT 0 NOT NULL;
