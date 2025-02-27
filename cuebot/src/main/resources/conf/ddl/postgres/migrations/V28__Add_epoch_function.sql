-- Create or replace the epoch function to fix issue with conversion of timestamp with timezone to account daylight
-- saving time
-- This function use postgresql internal extract and epoch function

CREATE OR REPLACE FUNCTION public.epoch(
timestamp with time zone)
    RETURNS numeric
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    t ALIAS FOR $1;
    delta integer;
BEGIN

    delta := extract(epoch from t);
    RETURN delta;
END;
$BODY$;
