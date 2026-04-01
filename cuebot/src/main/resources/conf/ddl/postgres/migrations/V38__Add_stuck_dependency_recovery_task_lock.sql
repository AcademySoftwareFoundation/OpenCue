-- Add task_lock entry for stuck dependency recovery maintenance task.
-- This task periodically detects and fixes frames stuck in DEPEND state
-- due to transient failures during dependency satisfaction.

INSERT INTO task_lock (pk_task_lock, str_name, int_lock, int_timeout)
VALUES ('00000000-0000-0000-0000-000000000007', 'LOCK_STUCK_DEPENDENCY_RECOVERY', 0, 600);
