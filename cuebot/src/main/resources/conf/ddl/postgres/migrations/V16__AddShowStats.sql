CREATE TABLE show_stats (
    pk_show VARCHAR(36) NOT NULL,
    int_frame_insert_count BIGINT DEFAULT 0 NOT NULL,
    int_job_insert_count BIGINT DEFAULT 0 NOT NULL,
    int_frame_success_count BIGINT DEFAULT 0 NOT NULL,
    int_frame_fail_count BIGINT DEFAULT 0 NOT NULL
);

INSERT INTO show_stats (
    pk_show,
    int_frame_insert_count,
    int_job_insert_count,
    int_frame_success_count,
    int_frame_fail_count
) SELECT
    pk_show,
    int_frame_insert_count,
    int_job_insert_count,
    int_frame_success_count,
    int_frame_fail_count
  FROM show;

CREATE UNIQUE INDEX c_show_stats_pk ON show_stats (pk_show);
ALTER TABLE show_stats ADD CONSTRAINT c_show_stats_pk PRIMARY KEY
  USING INDEX c_show_stats_pk;


-- Destructive changes. Please test changes above prior to executing this.
ALTER TABLE show
    DROP COLUMN int_frame_insert_count,
    DROP COLUMN int_job_insert_count,
    DROP COLUMN int_frame_success_count,
    DROP COLUMN int_frame_fail_count;
