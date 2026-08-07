-- Add task_lock entry for the orphaned frame check maintenance task.
-- This task kills and clears frames left RUNNING with no proc. It runs on its own Quartz trigger
-- and lock so it neither shares nor starves the hardware-state check's budget or lock.

INSERT INTO task_lock (pk_task_lock, str_name, int_lock, int_timeout)
VALUES ('00000000-0000-0000-0000-000000000008', 'LOCK_ORPHANED_FRAME_CHECK', 0, 300000);
