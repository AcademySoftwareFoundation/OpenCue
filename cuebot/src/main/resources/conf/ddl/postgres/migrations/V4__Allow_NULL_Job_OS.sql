-- Allow job to have NULL os field, meaning 'anything'.

ALTER TABLE "job" ALTER COLUMN "str_os" TYPE VARCHAR(12) NULL;