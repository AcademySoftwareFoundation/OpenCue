-- Increase the size of layer.str_range and layer.str_cmd.
--
-- A layer's range was VARCHAR(4000), which a fully enumerated frame list
-- (rather than a compact "start-end" range) can exceed for a job with a
-- few thousand frames, rolling back the job launch. str_cmd is widened for
-- the same reason: a command built from many joined paths can also exceed
-- 4000 characters.

ALTER TABLE layer ALTER COLUMN str_range TYPE text;
ALTER TABLE layer ALTER COLUMN str_cmd TYPE text;
