/**
* Add some columns to store virtual memory in use.
**/
ALTER TABLE proc ADD int_virt_used NUMERIC(16,0) DEFAULT 0 NOT NULL;
ALTER TABLE proc ADD int_virt_max_used NUMERIC(16,0) DEFAULT 0 NOT NULL;
