-- Add scheduled to frame
ALTER TABLE frame ADD COLUMN b_scheduled boolean DEFAULT false NOT NULL;
ALTER TABLE frame ADD COLUMN ts_scheduled timestamp(6) with time zone;
