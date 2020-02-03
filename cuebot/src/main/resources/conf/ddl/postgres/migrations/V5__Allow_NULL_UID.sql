-- Allow a NULL UID field, meaning 'RQD current user'.

ALTER TABLE "job" ALTER COLUMN "int_uid" DROP NOT NULL;
ALTER TABLE "job" ALTER COLUMN "int_uid" DROP DEFAULT;

