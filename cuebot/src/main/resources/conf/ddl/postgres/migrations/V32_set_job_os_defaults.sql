-- Update all existing entries to not have NULL values
UPDATE job
    SET str_os = ''
    WHERE str_os IS NULL;

-- Change default value
ALTER TABLE job
    ALTER COLUMN str_os SET DEFAULT '';

-- Make sure it's not NULL
ALTER TABLE job
    ALTER COLUMN str_os SET NOT NULL;
