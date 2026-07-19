-- Mark a layer as slot-based by requiring at least this many concurrency slots per frame.
-- 0 means the layer is not slot-based and books by cores/memory as usual.
alter table layer
    add int_slots_required INT DEFAULT 0 NOT NULL;
