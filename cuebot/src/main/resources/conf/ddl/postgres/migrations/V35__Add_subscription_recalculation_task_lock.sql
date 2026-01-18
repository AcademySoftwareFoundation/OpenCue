-- Add task_lock entry for subscription recalculation maintenance task
-- This task periodically recalculates subscription core usage values
-- to fix accountability issues that can occur at large scale.

INSERT INTO task_lock (pk_task_lock, str_name, int_lock, int_timeout)
VALUES ('00000000-0000-0000-0000-000000000006', 'LOCK_SUBSCRIPTION_RECALCULATION', 0, 7200);
