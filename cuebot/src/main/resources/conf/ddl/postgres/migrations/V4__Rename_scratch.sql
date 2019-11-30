-- Alter column names to renaming mcp to scratch

ALTER TABLE "host_stat" RENAME COLUMN int_mcp_total TO int_scratch_total;
ALTER TABLE "host_stat" RENAME COLUMN int_mcp_free TO int_scratch_free;
