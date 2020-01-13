-- Allow job to have NULL os field, meaning 'anything'.

ALTER TABLE "job" ALTER COLUMN "str_os" DROP NOT NULL;
ALTER TABLE "job" ALTER COLUMN "str_os" DROP DEFAULT;
