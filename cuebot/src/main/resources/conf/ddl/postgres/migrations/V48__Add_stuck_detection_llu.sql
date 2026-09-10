-- Minutes without progress (log, CPU, or IO) before RQD kills a frame as stuck.
-- 0 = stuck detection disabled.

ALTER TABLE show_service ADD COLUMN int_stuck_detection_llu INT DEFAULT 0 NOT NULL;
ALTER TABLE service ADD COLUMN int_stuck_detection_llu INT DEFAULT 0 NOT NULL;
ALTER TABLE layer ADD COLUMN int_stuck_detection_llu INT DEFAULT 0 NOT NULL;
