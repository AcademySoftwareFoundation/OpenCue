-- Host-based limits and external license reporting.
--
-- A limit now declares how it counts (per frame or per host), whether it gates
-- booking or only informs it, and which frame exit status means "this license
-- was unavailable". An external reporter (e.g. a sesictrl cron) can feed Cuebot
-- the license server's per-host view via limit_host; limit_usage caches the
-- settled totals so the dispatch gate reads one row per limit instead of
-- aggregating the farm.
--
-- DEPLOYMENT GATE: limit_record has no unique constraint on str_name today.
-- The constraints below fail loudly on a database that already has duplicate
-- limit names. Precheck with:
--   SELECT str_name, COUNT(*) FROM limit_record GROUP BY str_name HAVING COUNT(*) > 1;
-- and resolve duplicates (rename or delete, repointing layer_limit) first.
--
-- BACKWARDS COMPATIBILITY: this migration is additive -- no column or table is
-- removed -- so an older Cuebot can keep running against a migrated database,
-- and a rollback to one is safe. Every new column is NOT NULL with a default,
-- so the older INSERT statements (which do not name them) still work.
-- The two new uniqueness constraints are the only visible change to an older
-- Cuebot: creating a second limit with an existing name, or binding the same
-- limit to a layer twice, now raises a duplicate key error instead of silently
-- creating a row that corrupts the usage counts.

-- ---------------------------------------------------------------------------
-- limit_record: counting type, enforcement, thresholds, report metadata and
-- the failure rule migrated from the dispatcher.layer_delay.rules property.
-- ---------------------------------------------------------------------------

ALTER TABLE limit_record ADD COLUMN str_type          VARCHAR(16)  DEFAULT 'FRAME'    NOT NULL;
ALTER TABLE limit_record ADD COLUMN str_enforcement   VARCHAR(16)  DEFAULT 'ENFORCED' NOT NULL;
ALTER TABLE limit_record ADD COLUMN int_soft_value    INT          DEFAULT -1         NOT NULL;
ALTER TABLE limit_record ADD COLUMN ts_reported       TIMESTAMP(6) WITH TIME ZONE;
ALTER TABLE limit_record ADD COLUMN str_report_source VARCHAR(255);
ALTER TABLE limit_record ADD COLUMN int_report_ttl    INT          DEFAULT 900        NOT NULL;

ALTER TABLE limit_record ADD COLUMN int_exit_status   INT;
ALTER TABLE limit_record ADD COLUMN int_delay_minutes INT     DEFAULT 0    NOT NULL;
ALTER TABLE limit_record ADD COLUMN b_auto_tag        BOOLEAN DEFAULT true NOT NULL;

-- Carry over the dead flag from V2 rather than dropping the intent on the floor.
-- The column itself stays so the schema remains readable by older Cuebot builds;
-- str_type is authoritative from here on and nothing maintains b_host_limit.
UPDATE limit_record SET str_type = 'HOST' WHERE b_host_limit = true;
COMMENT ON COLUMN limit_record.b_host_limit IS 'Deprecated: superseded by str_type. Never read by any Cuebot version; kept only so pre-V49 builds see an unchanged schema. Not kept in sync.';

ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_pk PRIMARY KEY (pk_limit_record);
-- V12 indexed pk_limit_record by hand; the primary key above supersedes it.
DROP INDEX IF EXISTS i_limit_record_pk_limit_record;
ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_uk_name UNIQUE (str_name);
ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_ck_type
    CHECK (str_type IN ('FRAME', 'HOST'));
ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_ck_enforcement
    CHECK (str_enforcement IN ('ENFORCED', 'ADVISORY', 'DISABLED'));

-- 0 is success and 1 is the conventional catch-all failure; claiming either
-- would auto-tag most of the farm.
ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_ck_exit_status
    CHECK (int_exit_status IS NULL OR int_exit_status > 1);
ALTER TABLE limit_record ADD CONSTRAINT c_limit_record_ck_delay
    CHECK (int_delay_minutes >= 0);

-- Two limits claiming the same status have no sensible resolution.
CREATE UNIQUE INDEX i_limit_record_uk_exit_status
    ON limit_record (int_exit_status) WHERE int_exit_status IS NOT NULL;

-- ---------------------------------------------------------------------------
-- layer_limit: binding provenance, and the uniqueness that makes auto-tagging
-- safe. Every aggregate joining layer_limit counts a proc once per matching
-- row, so a duplicate binding doubles that layer's usage contribution.
-- ---------------------------------------------------------------------------

ALTER TABLE layer_limit ADD COLUMN str_source VARCHAR(16) DEFAULT 'SPEC' NOT NULL;
ALTER TABLE layer_limit ADD COLUMN ts_created TIMESTAMP(6) WITH TIME ZONE
    DEFAULT current_timestamp NOT NULL;

-- Collapse pre-existing duplicates. Unlike a limit_record name collision,
-- these rows are provably redundant -- same layer, same limit, no information
-- in either copy -- so repairing automatically is safe.
DELETE FROM layer_limit a
      USING layer_limit b
      WHERE a.pk_layer = b.pk_layer
        AND a.pk_limit_record = b.pk_limit_record
        AND a.pk_layer_limit > b.pk_layer_limit;

ALTER TABLE layer_limit ADD CONSTRAINT c_layer_limit_pk PRIMARY KEY (pk_layer_limit);
ALTER TABLE layer_limit ADD CONSTRAINT c_layer_limit_uk UNIQUE (pk_layer, pk_limit_record);
ALTER TABLE layer_limit ADD CONSTRAINT c_layer_limit_ck_source
    CHECK (str_source IN ('SPEC', 'AUTO', 'MANUAL'));
CREATE INDEX i_layer_limit_str_source ON layer_limit (pk_limit_record, str_source);

-- ---------------------------------------------------------------------------
-- limit_host: the license server's view of who holds a token. Keyed on the
-- normalized hostname, not pk_host: most holders are artist workstations with
-- no host row, and a re-registered render host keeps its name but not its id.
-- ---------------------------------------------------------------------------

CREATE TABLE limit_host (
    pk_limit_host     VARCHAR(36)  NOT NULL,
    pk_limit_record   VARCHAR(36)  NOT NULL,
    -- Normalized join key: short hostname, lowercased.
    str_host_name     VARCHAR(256) NOT NULL,
    -- As the license server reported it, for display.
    str_reported_name VARCHAR(256) NOT NULL,
    int_tokens        INT DEFAULT 1 NOT NULL,
    str_user          VARCHAR(64),
    -- Batch timestamp of the last report mentioning this host. Doubles as the
    -- sweep key in replaceExternalHolds; do not repurpose.
    ts_reported       TIMESTAMP(6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    CONSTRAINT c_limit_host_pk PRIMARY KEY (pk_limit_host),
    CONSTRAINT c_limit_host_uk UNIQUE (pk_limit_record, str_host_name),
    CONSTRAINT c_limit_host_ck_tokens CHECK (int_tokens > 0),
    CONSTRAINT c_limit_host_fk_limit FOREIGN KEY (pk_limit_record)
        REFERENCES limit_record (pk_limit_record) ON DELETE CASCADE
);

CREATE INDEX i_limit_host_str_host_name ON limit_host (str_host_name);

-- Reports rewrite a handful of rows every few seconds; keep the updates HOT
-- and autovacuum aggressive so the table never bloats.
ALTER TABLE limit_host SET (fillfactor = 70,
    autovacuum_vacuum_scale_factor = 0.0, autovacuum_vacuum_threshold = 500);

-- ---------------------------------------------------------------------------
-- limit_usage: precomputed settled totals so the dispatch gate reads one row
-- per limit. Refreshed by the LOCK_LIMIT_USAGE_RECALCULATION maintenance task
-- and synchronously by the report path.
-- ---------------------------------------------------------------------------

CREATE TABLE limit_usage (
    pk_limit_record    VARCHAR(36) NOT NULL,
    int_settled_usage  INT DEFAULT 0 NOT NULL,
    int_settled_hosts  INT DEFAULT 0 NOT NULL,
    ts_watermark       TIMESTAMP(6) WITH TIME ZONE,
    ts_updated         TIMESTAMP(6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    CONSTRAINT c_limit_usage_pk PRIMARY KEY (pk_limit_record),
    CONSTRAINT c_limit_usage_fk FOREIGN KEY (pk_limit_record)
        REFERENCES limit_record (pk_limit_record) ON DELETE CASCADE
);
ALTER TABLE limit_usage SET (fillfactor = 70);

INSERT INTO limit_usage (pk_limit_record)
    SELECT pk_limit_record FROM limit_record;

-- ---------------------------------------------------------------------------
-- Supporting index for the pending scan (procs dispatched after a limit's
-- settlement watermark).
-- ---------------------------------------------------------------------------

CREATE INDEX i_proc_ts_dispatched ON proc (ts_dispatched);

-- ---------------------------------------------------------------------------
-- Cross-instance lock for the limit_usage refresh task.
--
-- int_timeout is in milliseconds: MaintenanceDaoJdbc.lockTask compares
-- "now_ms - int_lock > int_timeout" where int_lock stores System.currentTimeMillis(), so
-- 60000 = 1 minute. (Some older seed rows predate this and look like seconds.)
-- ---------------------------------------------------------------------------

INSERT INTO task_lock (pk_task_lock, str_name, int_lock, int_timeout)
VALUES ('00000000-0000-0000-0000-000000000009', 'LOCK_LIMIT_USAGE_RECALCULATION', 0, 60000);
