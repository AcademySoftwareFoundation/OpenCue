-- Add a field to mark a layer as requiring at least a specific number of slots
-- <= 0 means slots are not required
alter table layer
    add int_slots_required INT NOT NULL DEFAULT 0;
