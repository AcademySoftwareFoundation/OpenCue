-- Change virt type from INT to BIGINT.

ALTER TABLE "proc" ALTER COLUMN "int_virt_used" TYPE BIGINT;
ALTER TABLE "proc" ALTER COLUMN "int_virt_max_used" TYPE BIGINT;
