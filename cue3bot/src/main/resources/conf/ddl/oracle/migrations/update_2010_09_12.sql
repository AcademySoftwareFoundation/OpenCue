
/**
* Add a flag to enable/disable optimizer.
*/
ALTER TABLE layer ADD b_optimize NUMERIC(1, 0) DEFAULT '1' NOT NULL;
