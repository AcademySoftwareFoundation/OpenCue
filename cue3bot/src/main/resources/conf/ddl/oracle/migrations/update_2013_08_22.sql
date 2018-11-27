ALTER TABLE layer_history ADD str_services VARCHAR2(128);
ALTER TABLE layer_history ADD str_tags VARCHAR2(4000);

CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_DELETE_LAYER" BEFORE DELETE ON layer
FOR EACH ROW
DECLARE
    TYPE StatType IS RECORD (
        int_core_time_success NUMERIC(38),
        int_core_time_fail NUMERIC(38),
        int_total_count NUMERIC(38),
        int_waiting_count NUMERIC(38),
        int_dead_count NUMERIC(38),
        int_depend_count NUMERIC(38),
        int_eaten_count NUMERIC(38),
        int_succeeded_count NUMERIC(38),
        int_running_count NUMERIC(38),
        int_max_rss NUMERIC(38),
        str_services VARCHAR2(128),
        str_tags VARCHAR2(4000)
    );
    js StatType;

BEGIN
    SELECT
        layer_usage.int_core_time_success,
        layer_usage.int_core_time_fail,
        layer_stat.int_total_count,
        layer_stat.int_waiting_count,
        layer_stat.int_dead_count,
        layer_stat.int_depend_count,
        layer_stat.int_eaten_count,
        layer_stat.int_succeeded_count,
        layer_stat.int_running_count,
        layer_mem.int_max_rss,
        :old.str_services,
        :old.str_tags
    INTO
        js
    FROM
        layer_mem,
        layer_usage,
        layer_stat
    WHERE
        layer_usage.pk_layer = layer_mem.pk_layer
    AND
        layer_stat.pk_layer = layer_mem.pk_layer
    AND
        layer_mem.pk_layer = :old.pk_layer;

    UPDATE
        layer_history
    SET
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_frame_count = js.int_total_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        str_services = js.str_services,
        str_tags = js.str_tags,
        b_archived = 1
    WHERE
        pk_layer = :old.pk_layer;

    delete from layer_resource where pk_layer=:old.pk_layer;
    delete from layer_stat where pk_layer=:old.pk_layer;
    delete from layer_usage where pk_layer=:old.pk_layer;
    delete from layer_env where pk_layer=:old.pk_layer;
    delete from layer_mem where pk_layer=:old.pk_layer;
    delete from layer_output where pk_layer=:old.pk_layer;
END;
