-- Add scheduled to frame
ALTER TABLE frame ADD COLUMN str_scheduled_by character varying(36) DEFAULT NULL;
ALTER TABLE frame ADD COLUMN ts_scheduled timestamp(6) with time zone;
