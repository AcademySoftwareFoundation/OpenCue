
-- Add minimum memory increase - default 2G

ALTER TABLE show_service ADD COLUMN int_min_memory_increase INT DEFAULT 2097152 NOT NULL;
ALTER TABLE service ADD COLUMN int_min_memory_increase INT DEFAULT 2097152 NOT NULL;
