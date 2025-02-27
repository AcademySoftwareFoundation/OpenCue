-- Add a new column to track swap memory usage in the proc table

ALTER TABLE proc ADD COLUMN int_swap_used BIGINT DEFAULT 0 NOT NULL;