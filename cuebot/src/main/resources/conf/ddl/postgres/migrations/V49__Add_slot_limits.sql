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
