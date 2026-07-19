-- Limit the max number of concurrent frames a host may run (slot-based host).
-- -1 means the host is not slot-based and books by cores/memory as usual.
-- When >= 0 the host only runs slot-based layers, capped at this many concurrent slots.
alter table host
    add int_concurrent_slots_limit INT DEFAULT -1 NOT NULL;
