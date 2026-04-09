-- Scheduler orchestrator tables for distributed cluster assignment (Mode 4)

CREATE TABLE scheduler_instance (
    pk_instance    UUID PRIMARY KEY,
    str_name       VARCHAR(256) NOT NULL,
    str_facility   VARCHAR(256),
    ts_heartbeat   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ts_registered  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    int_capacity   INTEGER NOT NULL DEFAULT 100,
    float_jobs_queried DOUBLE PRECISION NOT NULL DEFAULT 0,
    b_draining     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_scheduler_instance_heartbeat ON scheduler_instance(ts_heartbeat);

CREATE TABLE scheduler_cluster_assignment (
    pk_assignment    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pk_instance      UUID NOT NULL REFERENCES scheduler_instance(pk_instance) ON DELETE CASCADE,
    str_cluster_id   TEXT NOT NULL,
    str_cluster_json TEXT NOT NULL,
    int_version      INTEGER NOT NULL DEFAULT 0,
    ts_assigned      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(str_cluster_id)
);

CREATE INDEX idx_sca_instance ON scheduler_cluster_assignment(pk_instance);
