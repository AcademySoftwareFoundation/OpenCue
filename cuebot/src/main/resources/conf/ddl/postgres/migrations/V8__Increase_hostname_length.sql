-- Increase the length of hostnames for IPv6 address.

ALTER TABLE "host" ALTER COLUMN "str_name" TYPE VARCHAR(45);
ALTER TABLE "host_tag" ALTER COLUMN "str_tag" TYPE VARCHAR(45);
