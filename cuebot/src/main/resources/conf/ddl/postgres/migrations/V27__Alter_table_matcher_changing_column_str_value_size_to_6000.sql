-- Alter the table "matcher", changing the column str_value size from 4000 to 6000

alter table matcher alter column str_value type character varying(6000);
