--
-- PostgreSQL database dump
--

-- Dumped from database version 10.3
-- Dumped by pg_dump version 10.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: jobstattype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.jobstattype AS (
	int_core_time_success bigint,
	int_core_time_fail bigint,
	int_waiting_count bigint,
	int_dead_count bigint,
	int_depend_count bigint,
	int_eaten_count bigint,
	int_succeeded_count bigint,
	int_running_count bigint,
	int_max_rss bigint
);


--
-- Name: layerstattype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.layerstattype AS (
	int_core_time_success bigint,
	int_core_time_fail bigint,
	int_total_count bigint,
	int_waiting_count bigint,
	int_dead_count bigint,
	int_depend_count bigint,
	int_eaten_count bigint,
	int_succeeded_count bigint,
	int_running_count bigint,
	int_max_rss bigint
);


--
-- Name: calculate_core_hours(numeric, numeric, numeric, numeric, numeric, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_core_hours(numeric, numeric, numeric, numeric, numeric, numeric) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    int_ts_started ALIAS FOR $1;
    int_ts_stopped ALIAS FOR $2;
    int_start_report ALIAS FOR $3;
    int_stop_report ALIAS FOR $4;
    int_job_stopped ALIAS FOR $5;
    int_cores ALIAS FOR $6;

    int_started NUMERIC(12,0);
    int_stopped NUMERIC(12,0);
BEGIN
    IF int_cores = 0 THEN
        RETURN 0;
    END IF;

    int_started := int_ts_started;
    int_stopped := int_ts_stopped;

    IF int_stopped = 0 THEN
        int_stopped := int_job_stopped;
    END IF;

    IF int_stopped = 0 OR int_stopped > int_stop_report THEN
        int_stopped := int_stop_report;
    END IF;

    IF int_started < int_start_report THEN
        int_started := int_start_report;
    END IF;
    RETURN ((int_stopped - int_started) * (int_cores / 100) / 3600);
END;
$_$;


--
-- Name: epoch(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.epoch(timestamp with time zone) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    t ALIAS FOR $1;

    epoch_date TIMESTAMP(0) WITH TIME ZONE := TIMESTAMP '1970-01-01 00:00:00.00 +00:00';
    epoch_sec NUMERIC(12, 0);
    delta INTERVAL;
BEGIN
    delta := t - epoch_date;
    RETURN INTERVAL_TO_SECONDS(delta);
END;
$_$;


--
-- Name: epoch_to_ts(numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.epoch_to_ts(numeric) RETURNS timestamp without time zone
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN TO_TIMESTAMP('19700101000000', 'YYYYMMDDHH24MISS TZH:TZM')
        + NUMTODSINTERVAL(seconds, 'SECOND');
END;
$$;


--
-- Name: find_duration(timestamp without time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.find_duration(timestamp without time zone, timestamp without time zone) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    ts_started ALIAS FOR $1;
    ts_stopped ALIAS FOR $2;

    t_interval INTERVAL DAY TO SECOND;
    t_stopped TIMESTAMP(0);
BEGIN

    IF ts_started IS NULL THEN
        RETURN 0;
    END IF;

    IF ts_stopped IS NULL THEN
      t_stopped := current_timestamp;
    ELSE
      t_stopped := ts_stopped;
    END IF;

    t_interval := t_stopped - ts_started;

    RETURN ROUND((EXTRACT(DAY FROM t_interval) * 86400
        + EXTRACT(HOUR FROM t_interval) * 3600
        + EXTRACT(MINUTE FROM t_interval) * 60
        + EXTRACT(SECOND FROM t_interval)));
END;
$_$;


--
-- Name: genkey(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.genkey() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    str_result VARCHAR(36);
    guid VARCHAR(36) := uuid_generate_v1();
BEGIN
    str_result := SUBSTR(guid, 0,8) || '-' || SUBSTR(guid,8,4)
      || '-' || SUBSTR(guid,12,4) || '-' || SUBSTR(guid,16,4) || '-' || SUBSTR(guid,20,12);
    RETURN str_result;
END;
$$;


--
-- Name: history__period_clear(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.history__period_clear() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    DELETE FROM history_period;
    INSERT INTO history_period (pk) VALUES (uuid_generate_v1());

END;
$$;


--
-- Name: history__period_shift(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.history__period_shift() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    vTemp DATE;
BEGIN
    SELECT dt_end
    INTO vTemp
    FROM history_period;

    UPDATE history_period
    SET dt_begin = vTemp,
        dt_end = (SELECT current_timestamp FROM dual);

EXCEPTION
    WHEN no_data_found THEN
        INSERT INTO history_period (pk) VALUES (uuid_generate_v1());
        SELECT dt_end
        INTO vTemp
        FROM history_period;
    WHEN OTHERS THEN
        RAISE;
END;
$$;


--
-- Name: history__period_shift(date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.history__period_shift(date) RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
    piEndDate ALIAS FOR $1;
    vTemp DATE;
BEGIN
    SELECT dt_end
    INTO vTemp
    FROM history_period;

    UPDATE history_period
    SET dt_begin = vTemp,
    dt_end = (SELECT nvl(piEndDate, current_timestamp) FROM dual);

EXCEPTION
    WHEN no_data_found THEN
        INSERT INTO history_period (pk) VALUES (uuid_generate_v1());
        SELECT dt_end
        INTO vTemp
        FROM history_period;
    WHEN OTHERS THEN
        RAISE;
END;
$_$;


--
-- Name: interval_to_seconds(interval); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.interval_to_seconds(interval) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    intrvl ALIAS FOR $1;
BEGIN
   RETURN EXTRACT(DAY FROM intrvl) * 86400
         + EXTRACT(HOUR FROM intrvl) * 3600
         + EXTRACT(MINUTE FROM intrvl) * 60
         + EXTRACT(SECOND FROM intrvl);
END;
$_$;


--
-- Name: recalculate_subs(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recalculate_subs() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    r RECORD;
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  UPDATE subscription SET int_cores = 0;
  FOR r IN
    SELECT proc.pk_show, alloc.pk_alloc, sum(proc.int_cores_reserved) as c
    FROM proc, host, alloc
    WHERE proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc
    GROUP BY proc.pk_show, alloc.pk_alloc
  LOOP
    UPDATE subscription SET int_cores = r.c WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;

  END LOOP;
END;
$$;


--
-- Name: recalculate_tags(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recalculate_tags(character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
    str_host_id ALIAS FOR $1;

    tag RECORD;
    full_str_tag VARCHAR(256) := '';
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  FOR tag IN (SELECT str_tag FROM host_tag WHERE pk_host=str_host_id ORDER BY str_tag_type ASC, str_tag ASC) LOOP
    full_str_tag := full_str_tag || ' ' || tag.str_tag;
  END LOOP;

  EXECUTE 'UPDATE host SET str_tags=trim($1) WHERE pk_host=$2'
    USING full_str_tag, str_host_id;
END;
$_$;


--
-- Name: recurse_folder_parent_change(character varying, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.recurse_folder_parent_change(character varying, character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
    str_folder_id ALIAS FOR $1;
    str_parent_folder_id ALIAS FOR $2;

    int_parent_level BIGINT;
    subfolder RECORD;
BEGIN
    SELECT int_level+1 INTO
        int_parent_level
    FROM
        folder_level
    WHERE
        pk_folder = str_parent_folder_id;

    UPDATE
        folder_level
    SET
        int_level = int_parent_level
    WHERE
        pk_folder = str_folder_id;

    FOR subfolder IN
        SELECT pk_folder FROM folder
        WHERE pk_parent_folder = str_folder_id
    LOOP
        PERFORM recurse_folder_parent_change(subfolder.pk_folder, str_folder_id);
    END LOOP;
END;
$_$;


--
-- Name: rename_allocs(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.rename_allocs() RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
    alloc RECORD;
BEGIN
    FOR alloc IN
        SELECT alloc.pk_alloc, alloc.str_name AS aname,facility.str_name AS fname
        FROM alloc,facility
        WHERE alloc.pk_facility = facility.pk_facility
    LOOP
        EXECUTE 'UPDATE alloc SET str_name=$1 WHERE pk_alloc=$2' USING
            alloc.fname || '.' || alloc.aname, alloc.pk_alloc;
    END LOOP;
END;
$_$;


--
-- Name: render_weeks(date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.render_weeks(date) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    dt_end ALIAS FOR $1;

    int_weeks NUMERIC;
BEGIN
    int_weeks := (dt_end - (next_day(current_timestamp,'sunday')+7)) / 7.0;
    IF int_weeks < 1 THEN
      RETURN 1;
    ELSE
      RETURN int_weeks;
    END IF;
END;
$_$;


--
-- Name: reorder_filters(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reorder_filters(character varying) RETURNS void
    LANGUAGE plpgsql
    AS $_$
DECLARE
    p_str_show_id ALIAS FOR $1;

    f_new_order INT := 1.0;
    r_filter RECORD;
BEGIN
    FOR r_filter IN
        SELECT pk_filter
        FROM filter
        WHERE pk_show=p_str_show_id
        ORDER BY f_order ASC
    LOOP
        UPDATE filter SET f_order=f_new_order WHERE pk_filter = r_filter.pk_filter;
        f_new_order := f_new_order + 1.0;
    END LOOP;
END;
$_$;


--
-- Name: soft_tier(numeric, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.soft_tier(numeric, numeric) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    int_cores ALIAS FOR $1;
    int_min_cores ALIAS FOR $2;
BEGIN
  IF int_cores IS NULL THEN
      RETURN 0;
  END IF;
  IF int_min_cores = 0 OR int_cores >= int_min_cores THEN
      RETURN 1;
  ELSE
    IF int_cores = 0 THEN
        return int_min_cores * -1;
    ELSE
        RETURN int_cores / int_min_cores;
    END IF;
  END IF;
END;
$_$;


--
-- Name: tier(numeric, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.tier(numeric, numeric) RETURNS numeric
    LANGUAGE plpgsql
    AS $_$
DECLARE
    int_cores ALIAS FOR $1;
    int_min_cores ALIAS FOR $2;
BEGIN
  IF int_min_cores = 0 THEN
       RETURN (int_cores / 100) + 1;
  ELSE
    IF int_cores = 0 THEN
        return int_min_cores * -1;
    ELSE
        RETURN int_cores / int_min_cores;
    END IF;
  END IF;
END;
$_$;


--
-- Name: tmp_populate_folder(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.tmp_populate_folder() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_folder, pk_show, sum(int_cores) AS c
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP by pk_folder, pk_show
    LOOP
        UPDATE folder_resource SET int_cores = t.c WHERE pk_folder = t.pk_folder;
        COMMIT;
    END LOOP;
END;
$$;


--
-- Name: tmp_populate_point(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.tmp_populate_point() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_dept, pk_show, sum(int_cores) AS c
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP BY pk_dept, pk_show
    LOOP
        UPDATE point SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_dept = t.pk_dept;
    END LOOP;
END;
$$;


--
-- Name: tmp_populate_sub(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.tmp_populate_sub() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT proc.pk_show, host.pk_alloc, sum(int_cores_reserved) AS c
        FROM proc, host
        WHERE proc.pk_host = host.pk_host
        GROUP BY proc.pk_show, host.pk_alloc
    LOOP
        UPDATE subscription SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_alloc = t.pk_alloc;
    END LOOP;
END;
$$;


--
-- Name: trigger__after_insert_folder(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_insert_folder() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    int_level INT := 0;
BEGIN
    IF NEW.pk_parent_folder IS NOT NULL THEN
        SELECT folder_level.int_level + 1 INTO int_level FROM folder_level WHERE pk_folder = NEW.pk_parent_folder;
    END IF;
    INSERT INTO folder_level (pk_folder_level, pk_folder, int_level) VALUES (NEW.pk_folder, NEW.pk_folder, int_level);
    INSERT INTO folder_resource (pk_folder_resource, pk_folder) VALUES (NEW.pk_folder, NEW.pk_folder);
    RETURN NULL;
END;
$$;


--
-- Name: trigger__after_insert_job(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_insert_job() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO job_stat (pk_job_stat,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_resource (pk_job_resource,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_usage (pk_job_usage,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_mem (pk_job_mem,pk_job) VALUES (NEW.pk_job,NEW.pk_job);

    INSERT INTO job_history
        (pk_job, pk_show, pk_facility, pk_dept, str_name, str_shot, str_user, int_ts_started)
    VALUES
        (NEW.pk_job, NEW.pk_show, NEW.pk_facility, NEW.pk_dept,
         NEW.str_name, NEW.str_shot, NEW.str_user, epoch(current_timestamp));

    RETURN NULL;
END;
$$;


--
-- Name: trigger__after_insert_layer(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_insert_layer() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);

    INSERT INTO layer_history
        (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, b_archived,str_services)
    VALUES
        (NEW.pk_layer, NEW.pk_job, NEW.str_name, NEW.str_type, NEW.int_cores_min, NEW.int_mem_min, false, NEW.str_services);

    RETURN NEW;
END;
$$;


--
-- Name: trigger__after_job_dept_update(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_job_dept_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    int_running_cores INT;
BEGIN
  /**
  * Handles the accounting for moving a job between departments.
  **/
  SELECT int_cores INTO int_running_cores
    FROM job_resource WHERE pk_job = NEW.pk_job;

  IF int_running_cores > 0 THEN
    UPDATE point SET int_cores = int_cores + int_running_cores
        WHERE pk_dept = NEW.pk_dept AND pk_show = NEW.pk_show;

    UPDATE point SET int_cores = int_cores - int_running_cores
        WHERE pk_dept = OLD.pk_dept AND pk_show = OLD.pk_show;
  END IF;

  RETURN NULL;
END;
$$;


--
-- Name: trigger__after_job_finished(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_job_finished() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    ts INT := epoch(current_timestamp);
    js JobStatType;
    ls LayerStatType;
    one_layer RECORD;
BEGIN
    SELECT
        job_usage.int_core_time_success,
        job_usage.int_core_time_fail,
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss
    INTO
        js
    FROM
        job_mem,
        job_usage,
        job_stat
    WHERE
        job_usage.pk_job = job_mem.pk_job
    AND
        job_stat.pk_job = job_mem.pk_job
    AND
        job_mem.pk_job = NEW.pk_job;

    UPDATE
        job_history
    SET
        pk_dept = NEW.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_frame_count = NEW.int_frame_count,
        int_layer_count = NEW.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        int_ts_stopped = ts
    WHERE
        pk_job = NEW.pk_job;

    FOR one_layer IN (SELECT pk_layer from layer where pk_job = NEW.pk_job)
    LOOP
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
            layer_mem.int_max_rss
        INTO
            ls
        FROM
            layer_mem,
            layer_usage,
            layer_stat
        WHERE
            layer_usage.pk_layer = layer_mem.pk_layer
        AND
            layer_stat.pk_layer = layer_mem.pk_layer
        AND
            layer_mem.pk_layer = one_layer.pk_layer;

        UPDATE
            layer_history
        SET
            int_core_time_success = ls.int_core_time_success,
            int_core_time_fail = ls.int_core_time_fail,
            int_frame_count = ls.int_total_count,
            int_waiting_count = ls.int_waiting_count,
            int_dead_count = ls.int_dead_count,
            int_depend_count = ls.int_depend_count,
            int_eaten_count = ls.int_eaten_count,
            int_succeeded_count = ls.int_succeeded_count,
            int_running_count = ls.int_running_count,
            int_max_rss = ls.int_max_rss
        WHERE
            pk_layer = one_layer.pk_layer;
    END LOOP;

    /**
     * Delete any local core assignments from this job.
     **/
    DELETE FROM job_local WHERE pk_job=NEW.pk_job;

    RETURN NEW;
END;
$$;


--
-- Name: trigger__after_job_moved(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__after_job_moved() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    int_core_count INT;
BEGIN
    SELECT int_cores INTO int_core_count
    FROM job_resource WHERE pk_job = NEW.pk_job;

    IF int_core_count > 0 THEN
        UPDATE folder_resource SET int_cores = int_cores + int_core_count
        WHERE pk_folder = NEW.pk_folder;

        UPDATE folder_resource  SET int_cores = int_cores - int_core_count
        WHERE pk_folder = OLD.pk_folder;
    END IF;
    RETURN NULL;
END
$$;


--
-- Name: trigger__before_delete_folder(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_delete_folder() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM folder_level WHERE pk_folder = OLD.pk_folder;
    DELETE FROM folder_resource WHERE pk_folder = OLD.pk_folder;
    RETURN OLD;
END;
$$;


--
-- Name: trigger__before_delete_host(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_delete_host() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM host_stat WHERE pk_host = OLD.pk_host;
    DELETE FROM host_tag WHERE pk_host = OLD.pk_host;
    DELETE FROM deed WHERE pk_host = OLD.pk_host;
    RETURN OLD;
END;
$$;


--
-- Name: trigger__before_delete_job(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_delete_job() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    js JobStatType;
BEGIN
    SELECT
        job_usage.int_core_time_success,
        job_usage.int_core_time_fail,
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss
    INTO
        js
    FROM
        job_mem,
        job_usage,
        job_stat
    WHERE
        job_usage.pk_job = job_mem.pk_job
    AND
        job_stat.pk_job = job_mem.pk_job
    AND
        job_mem.pk_job = OLD.pk_job;

    UPDATE
        job_history
    SET
        pk_dept = OLD.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_frame_count = OLD.int_frame_count,
        int_layer_count = OLD.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        b_archived = 1,
        int_ts_stopped = nvl(epoch(OLD.ts_stopped), epoch(current_timestamp))
    WHERE
        pk_job = OLD.pk_job;

    DELETE FROM depend WHERE pk_job_depend_on=OLD.pk_job OR pk_job_depend_er=OLD.pk_job;
    DELETE FROM frame WHERE pk_job=OLD.pk_job;
    DELETE FROM layer WHERE pk_job=OLD.pk_job;
    DELETE FROM job_env WHERE pk_job=OLD.pk_job;
    DELETE FROM job_stat WHERE pk_job=OLD.pk_job;
    DELETE FROM job_resource WHERE pk_job=OLD.pk_job;
    DELETE FROM job_usage WHERE pk_job=OLD.pk_job;
    DELETE FROM job_mem WHERE pk_job=OLD.pk_job;
    DELETE FROM comments WHERE pk_job=OLD.pk_job;

    RETURN OLD;
END
$$;


--
-- Name: trigger__before_delete_layer(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_delete_layer() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    js LayerStatType;
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
        layer_mem.int_max_rss
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
        layer_mem.pk_layer = OLD.pk_layer;

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
        b_archived = 1
    WHERE
        pk_layer = OLD.pk_layer;

    DELETE FROM layer_resource where pk_layer=OLD.pk_layer;
    DELETE FROM layer_stat where pk_layer=OLD.pk_layer;
    DELETE FROM layer_usage where pk_layer=OLD.pk_layer;
    DELETE FROM layer_env where pk_layer=OLD.pk_layer;
    DELETE FROM layer_mem where pk_layer=OLD.pk_layer;
    DELETE FROM layer_output where pk_layer=OLD.pk_layer;

    RETURN OLD;
END;
$$;


--
-- Name: trigger__before_insert_folder(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_insert_folder() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.pk_parent_folder IS NULL THEN
        NEW.b_default := 1;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__before_insert_proc(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__before_insert_proc() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.int_cores_reserved <= 0 THEN
        RAISE EXCEPTION 'failed to allocate proc, tried to allocate 0 cores';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__frame_history_open(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__frame_history_open() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
  str_pk_alloc VARCHAR(36) := null;
  int_checkpoint INT := 0;
BEGIN

    IF OLD.str_state = 'Running' THEN

        IF NEW.int_exit_status = 299 THEN

          EXECUTE 'DELETE FROM frame_history WHERE int_ts_stopped = 0 AND pk_frame=$1' USING
            NEW.pk_frame;

        ELSE
          If NEW.str_state = 'Checkpoint' THEN
              int_checkpoint := 1;
          END IF;

          EXECUTE
          'UPDATE
              frame_history
          SET
              int_mem_max_used=$1,
              int_ts_stopped=$2,
              int_exit_status=$3,
              int_checkpoint_count=$4
          WHERE
              int_ts_stopped = 0 AND pk_frame=$5'
          USING
              NEW.int_mem_max_used,
              epoch(current_timestamp),
              NEW.int_exit_status,
              int_checkpoint,
              NEW.pk_frame;
        END IF;
    END IF;

    IF NEW.str_state = 'Running' THEN

      SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=NEW.str_host;

      EXECUTE
        'INSERT INTO
            frame_history
        (
            pk_frame,
            pk_layer,
            pk_job,
            str_name,
            str_state,
            int_cores,
            int_mem_reserved,
            str_host,
            int_ts_started,
            pk_alloc
         )
         VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)'
         USING NEW.pk_frame,
            NEW.pk_layer,
            NEW.pk_job,
            NEW.str_name,
            'Running',
            NEW.int_cores,
            NEW.int_mem_reserved,
            NEW.str_host,
            epoch(current_timestamp),
            str_pk_alloc;
    END IF;
    RETURN NULL;

END;
$_$;


--
-- Name: trigger__point_tier(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__point_tier() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /* calcultes a soft tier */
    NEW.float_tier := soft_tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tbiu_frame_history(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tbiu_frame_history() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tbiu_job_history(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tbiu_job_history() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tbiu_layer_history(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tbiu_layer_history() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END
$$;


--
-- Name: trigger__tier_folder(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tier_folder() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /** calculates new tier **/
    NEW.float_tier := soft_tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tier_host_local(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tier_host_local() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.float_tier := tier(NEW.int_cores_max - NEW.int_cores_idle,NEW.int_cores_max);
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tier_job(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tier_job() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /** calculates new tier **/
    NEW.float_tier := tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$$;


--
-- Name: trigger__tier_subscription(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__tier_subscription() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /* calcultes a soft tier */
    NEW.float_tier := tier(NEW.int_cores, NEW.int_size);
    RETURN NEW;
END;
$$;


--
-- Name: trigger__update_frame_checkpoint_state(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_frame_checkpoint_state() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.str_state := 'Checkpoint';
    RETURN NEW;
END;
$$;


--
-- Name: trigger__update_frame_dep_to_wait(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_frame_dep_to_wait() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.str_state := 'Waiting';
    NEW.ts_updated := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__update_frame_eaten(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_frame_eaten() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.str_state := 'Succeeded';
    RETURN NEW;
END;
$$;


--
-- Name: trigger__update_frame_status_counts(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_frame_status_counts() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    s_old_status_col VARCHAR(32);
    s_new_status_col VARCHAR(32);
BEGIN
    s_old_status_col := 'int_' || OLD.str_state || '_count';
    s_new_status_col := 'int_' || NEW.str_state || '_count';

    EXECUTE 'UPDATE layer_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_layer=$1' USING NEW.pk_layer;

    EXECUTE 'UPDATE job_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_job=$1' USING NEW.pk_job;
    RETURN NULL;
END;
$_$;


--
-- Name: trigger__update_frame_wait_to_dep(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_frame_wait_to_dep() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.str_state := 'Depend';
    NEW.ts_updated := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__update_proc_update_layer(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__update_proc_update_layer() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    lr RECORD;
BEGIN
     FOR lr IN (
        SELECT
          pk_layer
        FROM
          layer_stat
        WHERE
          pk_layer IN (OLD.pk_layer, NEW.pk_layer)
        ORDER BY layer_stat.pk_layer DESC
        ) LOOP

      IF lr.pk_layer = OLD.pk_layer THEN

        UPDATE layer_resource SET
          int_cores = int_cores - OLD.int_cores_reserved
        WHERE
          pk_layer = OLD.pk_layer;

      ELSE

        UPDATE layer_resource SET
          int_cores = int_cores + NEW.int_cores_reserved
       WHERE
          pk_layer = NEW.pk_layer;
       END IF;

    END LOOP;
    RETURN NULL;
END;
$$;


--
-- Name: trigger__upgrade_proc_memory_usage(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__upgrade_proc_memory_usage() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE host SET
        int_mem_idle = int_mem_idle - (NEW.int_mem_reserved - OLD.int_mem_reserved)
    WHERE
        pk_host = NEW.pk_host;
    RETURN NULL;
END;
$$;


--
-- Name: trigger__verify_host_local(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__verify_host_local() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF NEW.int_cores_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough idle cores.';
    END IF;

    IF NEW.int_mem_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough idle memory';
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trigger__verify_host_resources(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__verify_host_resources() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.int_cores_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional core units';
    END IF;

    If NEW.int_mem_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional memory';
    END IF;

    If NEW.int_gpu_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional gpu memory';
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trigger__verify_job_local(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__verify_job_local() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF NEW.int_cores > NEW.int_max_cores THEN
        RAISE EXCEPTION 'job local has exceeded max cores';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__verify_job_resources(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__verify_job_resources() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * at the wrong time.
    **/
    IF NEW.int_cores > NEW.int_max_cores THEN
        RAISE EXCEPTION 'job has exceeded max cores';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger__verify_subscription(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger__verify_subscription() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    /**
    * Check to see if adding more procs will push the show over
    * its subscription size.  This check is only done when
    * new.int_burst = old.int_burst and new.int_cores > old.int cores,
    * otherwise this error would be thrown at the wrong time.
    **/
    IF NEW.int_cores > NEW.int_burst THEN
        RAISE EXCEPTION 'subscription has exceeded burst size';
    END IF;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: action; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action (
    pk_action character varying(36) NOT NULL,
    pk_filter character varying(36) NOT NULL,
    pk_folder character varying(36),
    str_action character varying(24) NOT NULL,
    str_value_type character varying(24) NOT NULL,
    str_value character varying(4000),
    int_value bigint,
    b_value boolean,
    ts_created timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    float_value numeric(6,2),
    b_stop boolean DEFAULT false NOT NULL
);


--
-- Name: alloc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alloc (
    pk_alloc character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_allow_edit boolean DEFAULT true NOT NULL,
    b_default boolean DEFAULT false NOT NULL,
    str_tag character varying(24),
    b_billable boolean DEFAULT true NOT NULL,
    pk_facility character varying(36) NOT NULL,
    b_enabled boolean DEFAULT true
);


--
-- Name: comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comments (
    pk_comment character varying(36) NOT NULL,
    pk_job character varying(36),
    pk_host character varying(36),
    ts_created timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    str_user character varying(36) NOT NULL,
    str_subject character varying(128) NOT NULL,
    str_message character varying(4000) NOT NULL
);


--
-- Name: config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.config (
    pk_config character varying(36) NOT NULL,
    str_key character varying(36) NOT NULL,
    int_value bigint DEFAULT 0,
    long_value bigint DEFAULT 0,
    str_value character varying(255) DEFAULT ''::character varying,
    b_value boolean DEFAULT false
);


--
-- Name: deed; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deed (
    pk_deed character varying(36) NOT NULL,
    pk_owner character varying(36) NOT NULL,
    pk_host character varying(36) NOT NULL,
    b_blackout boolean DEFAULT false NOT NULL,
    int_blackout_start integer,
    int_blackout_stop integer
);


--
-- Name: depend; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.depend (
    pk_depend character varying(36) NOT NULL,
    pk_parent character varying(36),
    pk_job_depend_on character varying(36) NOT NULL,
    pk_job_depend_er character varying(36) NOT NULL,
    pk_frame_depend_on character varying(36),
    pk_frame_depend_er character varying(36),
    pk_layer_depend_on character varying(36),
    pk_layer_depend_er character varying(36),
    str_type character varying(36) NOT NULL,
    b_active boolean DEFAULT true NOT NULL,
    b_any boolean DEFAULT false NOT NULL,
    ts_created timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_satisfied timestamp(6) without time zone,
    str_target character varying(20) DEFAULT 'Internal'::character varying NOT NULL,
    str_signature character varying(36) NOT NULL,
    b_composite boolean DEFAULT false NOT NULL
);


--
-- Name: dept; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dept (
    pk_dept character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_default boolean DEFAULT false NOT NULL
);


--
-- Name: duplicate_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.duplicate_cursors (
    dt_recorded date,
    inst_id numeric,
    lng_count numeric
);


--
-- Name: facility; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facility (
    pk_facility character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_default boolean DEFAULT false NOT NULL
);


--
-- Name: filter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.filter (
    pk_filter character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_name character varying(128) NOT NULL,
    str_type character varying(16) NOT NULL,
    f_order numeric(6,2) DEFAULT 0.0 NOT NULL,
    b_enabled boolean DEFAULT true NOT NULL
);


--
-- Name: flyway_schema_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.flyway_schema_history (
    installed_rank integer NOT NULL,
    version character varying(50),
    description character varying(200) NOT NULL,
    type character varying(20) NOT NULL,
    script character varying(1000) NOT NULL,
    checksum integer,
    installed_by character varying(100) NOT NULL,
    installed_on timestamp without time zone DEFAULT now() NOT NULL,
    execution_time integer NOT NULL,
    success boolean NOT NULL
);


--
-- Name: folder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder (
    pk_folder character varying(36) NOT NULL,
    pk_parent_folder character varying(36),
    pk_show character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    int_priority bigint DEFAULT 1 NOT NULL,
    b_default boolean DEFAULT false NOT NULL,
    pk_dept character varying(36) NOT NULL,
    int_job_min_cores integer DEFAULT '-1'::integer NOT NULL,
    int_job_max_cores integer DEFAULT '-1'::integer NOT NULL,
    int_job_priority integer DEFAULT '-1'::integer NOT NULL,
    int_min_cores integer DEFAULT 0 NOT NULL,
    int_max_cores integer DEFAULT '-1'::integer NOT NULL,
    b_exclude_managed boolean DEFAULT false NOT NULL,
    f_order integer DEFAULT 0 NOT NULL
);


--
-- Name: folder_level; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder_level (
    pk_folder_level character varying(36) NOT NULL,
    pk_folder character varying(36) NOT NULL,
    int_level bigint DEFAULT 0 NOT NULL
);


--
-- Name: folder_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder_resource (
    pk_folder_resource character varying(36) NOT NULL,
    pk_folder character varying(36) NOT NULL,
    int_cores integer DEFAULT 0 NOT NULL,
    int_max_cores integer DEFAULT '-1'::integer NOT NULL,
    int_min_cores integer DEFAULT 0 NOT NULL,
    float_tier numeric(16,2) DEFAULT 0 NOT NULL
);


--
-- Name: frame; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.frame (
    pk_frame character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    str_name character varying(256) NOT NULL,
    str_state character varying(24) NOT NULL,
    int_number bigint NOT NULL,
    int_depend_count bigint DEFAULT 0 NOT NULL,
    int_exit_status bigint DEFAULT '-1'::integer NOT NULL,
    int_retries bigint DEFAULT 0 NOT NULL,
    int_mem_reserved bigint DEFAULT 0 NOT NULL,
    int_mem_max_used bigint DEFAULT 0 NOT NULL,
    int_mem_used bigint DEFAULT 0 NOT NULL,
    int_dispatch_order bigint DEFAULT 0 NOT NULL,
    str_host character varying(256),
    int_cores integer DEFAULT 0 NOT NULL,
    int_layer_order integer NOT NULL,
    ts_started timestamp(6) with time zone,
    ts_stopped timestamp(6) with time zone,
    ts_last_run timestamp(6) with time zone,
    ts_updated timestamp(6) with time zone,
    int_version integer DEFAULT 0,
    str_checkpoint_state character varying(12) DEFAULT 'Disabled'::character varying NOT NULL,
    int_checkpoint_count smallint DEFAULT 0 NOT NULL,
    int_gpu_reserved integer DEFAULT 0 NOT NULL,
    int_total_past_core_time integer DEFAULT 0 NOT NULL
);


--
-- Name: frame_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.frame_history (
    pk_frame_history character varying(36) DEFAULT public.uuid_generate_v1() NOT NULL,
    pk_frame character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    str_name character varying(256) NOT NULL,
    str_state character varying(24) NOT NULL,
    int_mem_reserved bigint DEFAULT 0 NOT NULL,
    int_mem_max_used bigint DEFAULT 0 NOT NULL,
    int_cores integer DEFAULT 100 NOT NULL,
    str_host character varying(64) DEFAULT NULL::character varying,
    int_exit_status smallint DEFAULT '-1'::integer NOT NULL,
    pk_alloc character varying(36),
    int_ts_started integer NOT NULL,
    int_ts_stopped integer DEFAULT 0 NOT NULL,
    int_checkpoint_count integer DEFAULT 0 NOT NULL,
    dt_last_modified date NOT NULL
);


--
-- Name: COLUMN frame_history.int_mem_reserved; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.frame_history.int_mem_reserved IS 'kilobytes of memory reserved';


--
-- Name: COLUMN frame_history.int_mem_max_used; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.frame_history.int_mem_max_used IS 'maximum kilobytes of rss memory used';


--
-- Name: COLUMN frame_history.int_cores; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.frame_history.int_cores IS '100 cores per physical core';


--
-- Name: history_period; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.history_period (
    pk character varying(36) DEFAULT public.uuid_generate_v1() NOT NULL,
    dt_begin date DEFAULT to_date('01-JAN-2000'::text, 'DD-MON-YYYY'::text) NOT NULL,
    dt_end date DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: history_period_bak; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.history_period_bak (
    pk character varying(32),
    dt_begin date NOT NULL,
    dt_end date NOT NULL
);


--
-- Name: host; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.host (
    pk_host character varying(36) NOT NULL,
    pk_alloc character varying(36) NOT NULL,
    str_name character varying(30) NOT NULL,
    str_lock_state character varying(36) NOT NULL,
    b_nimby boolean DEFAULT false NOT NULL,
    ts_created timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    int_cores bigint DEFAULT 0 NOT NULL,
    int_procs bigint DEFAULT 0 NOT NULL,
    int_cores_idle bigint DEFAULT 0 NOT NULL,
    int_mem bigint DEFAULT 0 NOT NULL,
    int_mem_idle bigint DEFAULT 0 NOT NULL,
    b_unlock_boot boolean DEFAULT false NOT NULL,
    b_unlock_idle boolean DEFAULT false NOT NULL,
    b_reboot_idle boolean DEFAULT false NOT NULL,
    str_tags character varying(128),
    str_fqdn character varying(128),
    b_comment boolean DEFAULT false NOT NULL,
    int_thread_mode integer DEFAULT 0 NOT NULL,
    str_lock_source character varying(128),
    int_gpu integer DEFAULT 0 NOT NULL,
    int_gpu_idle integer DEFAULT 0 NOT NULL
);


--
-- Name: host_local; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.host_local (
    pk_host_local character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    pk_layer character varying(36),
    pk_frame character varying(36),
    pk_host character varying(36) NOT NULL,
    ts_created timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_updated timestamp(6) with time zone,
    int_mem_max integer DEFAULT 0 NOT NULL,
    int_mem_idle integer DEFAULT 0 NOT NULL,
    int_cores_max integer DEFAULT 100 NOT NULL,
    int_cores_idle integer DEFAULT 100 NOT NULL,
    int_threads integer DEFAULT 1 NOT NULL,
    float_tier numeric(16,2) DEFAULT 0 NOT NULL,
    b_active boolean DEFAULT true NOT NULL,
    str_type character varying(36) NOT NULL,
    int_gpu_idle integer DEFAULT 0 NOT NULL,
    int_gpu_max integer DEFAULT 0 NOT NULL
);


--
-- Name: host_stat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.host_stat (
    pk_host_stat character varying(36) NOT NULL,
    pk_host character varying(36) NOT NULL,
    int_mem_total bigint DEFAULT 0 NOT NULL,
    int_mem_free bigint DEFAULT 0 NOT NULL,
    int_swap_total bigint DEFAULT 0 NOT NULL,
    int_swap_free bigint DEFAULT 0 NOT NULL,
    int_mcp_total bigint DEFAULT 0 NOT NULL,
    int_mcp_free bigint DEFAULT 0 NOT NULL,
    int_load bigint DEFAULT 0 NOT NULL,
    ts_ping timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_booted timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    str_state character varying(32) DEFAULT 'Up'::character varying NOT NULL,
    str_os character varying(12) DEFAULT 'rhel40'::character varying NOT NULL,
    int_gpu_total integer DEFAULT 0 NOT NULL,
    int_gpu_free integer DEFAULT 0 NOT NULL
);


--
-- Name: host_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.host_tag (
    pk_host_tag character varying(36) NOT NULL,
    pk_host character varying(36) NOT NULL,
    str_tag character varying(36) NOT NULL,
    str_tag_type character varying(24) DEFAULT 'Hardware'::character varying NOT NULL,
    b_constant boolean DEFAULT false NOT NULL
);


--
-- Name: job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job (
    pk_job character varying(36) NOT NULL,
    pk_folder character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_name character varying(255) NOT NULL,
    str_visible_name character varying(255),
    str_shot character varying(64) NOT NULL,
    str_user character varying(32) NOT NULL,
    str_state character varying(16) NOT NULL,
    str_log_dir character varying(4000) DEFAULT ''::character varying NOT NULL,
    int_uid bigint DEFAULT 0 NOT NULL,
    b_paused boolean DEFAULT false NOT NULL,
    b_autoeat boolean DEFAULT false NOT NULL,
    int_frame_count integer DEFAULT 0 NOT NULL,
    int_layer_count integer DEFAULT 0 NOT NULL,
    int_max_retries smallint DEFAULT 3 NOT NULL,
    b_auto_book boolean DEFAULT true NOT NULL,
    b_auto_unbook boolean DEFAULT true NOT NULL,
    b_comment boolean DEFAULT false NOT NULL,
    str_email character varying(256),
    pk_facility character varying(36) NOT NULL,
    pk_dept character varying(36) NOT NULL,
    ts_started timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_stopped timestamp(6) with time zone,
    int_min_cores integer DEFAULT 100 NOT NULL,
    int_max_cores integer DEFAULT 20000 NOT NULL,
    str_show character varying(32) DEFAULT 'none'::character varying NOT NULL,
    ts_updated timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    str_os character varying(12) DEFAULT 'rhel40'::character varying NOT NULL
);


--
-- Name: job_env; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_env (
    pk_job_env character varying(36) NOT NULL,
    pk_job character varying(36),
    str_key character varying(36),
    str_value character varying(2048)
);


--
-- Name: job_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_history (
    pk_job character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_name character varying(512) NOT NULL,
    str_shot character varying(64) NOT NULL,
    str_user character varying(36) NOT NULL,
    int_core_time_success bigint DEFAULT 0 NOT NULL,
    int_core_time_fail bigint DEFAULT 0 NOT NULL,
    int_frame_count bigint DEFAULT 0 NOT NULL,
    int_layer_count bigint DEFAULT 0 NOT NULL,
    int_waiting_count bigint DEFAULT 0 NOT NULL,
    int_dead_count bigint DEFAULT 0 NOT NULL,
    int_depend_count bigint DEFAULT 0 NOT NULL,
    int_eaten_count bigint DEFAULT 0 NOT NULL,
    int_succeeded_count bigint DEFAULT 0 NOT NULL,
    int_running_count bigint DEFAULT 0 NOT NULL,
    int_max_rss bigint DEFAULT 0 NOT NULL,
    b_archived boolean DEFAULT false NOT NULL,
    pk_facility character varying(36) NOT NULL,
    pk_dept character varying(36) NOT NULL,
    int_ts_started integer NOT NULL,
    int_ts_stopped integer DEFAULT 0 NOT NULL,
    dt_last_modified date NOT NULL
);


--
-- Name: COLUMN job_history.int_core_time_success; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.job_history.int_core_time_success IS 'seconds per core succeeded';


--
-- Name: COLUMN job_history.int_core_time_fail; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.job_history.int_core_time_fail IS 'seconds per core failed';


--
-- Name: COLUMN job_history.int_max_rss; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.job_history.int_max_rss IS 'maximum kilobytes of rss memory used by a single frame';


--
-- Name: job_local; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_local (
    pk_job_local character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    pk_host character varying(36) NOT NULL,
    str_source character varying(255) NOT NULL,
    ts_created timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    int_cores integer DEFAULT 0 NOT NULL,
    int_max_cores integer NOT NULL
);


--
-- Name: job_mem; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_mem (
    pk_job_mem character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_max_rss integer DEFAULT 0 NOT NULL,
    int_max_vss integer DEFAULT 0 NOT NULL
);


--
-- Name: job_post; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_post (
    pk_job_post character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    pk_post_job character varying(36) NOT NULL
);


--
-- Name: job_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_resource (
    pk_job_resource character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_cores bigint DEFAULT 0 NOT NULL,
    int_max_rss integer DEFAULT 0 NOT NULL,
    int_max_vss integer DEFAULT 0 NOT NULL,
    int_min_cores integer DEFAULT 100 NOT NULL,
    int_max_cores integer DEFAULT 10000 NOT NULL,
    float_tier numeric(16,2) DEFAULT 0 NOT NULL,
    int_priority integer DEFAULT 1 NOT NULL,
    int_local_cores integer DEFAULT 0 NOT NULL
);


--
-- Name: job_stat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_stat (
    pk_job_stat character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_waiting_count bigint DEFAULT 0 NOT NULL,
    int_running_count bigint DEFAULT 0 NOT NULL,
    int_dead_count bigint DEFAULT 0 NOT NULL,
    int_depend_count bigint DEFAULT 0 NOT NULL,
    int_eaten_count bigint DEFAULT 0 NOT NULL,
    int_succeeded_count bigint DEFAULT 0 NOT NULL,
    int_checkpoint_count bigint DEFAULT 0 NOT NULL
);


--
-- Name: job_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_usage (
    pk_job_usage character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_core_time_success bigint DEFAULT 0 NOT NULL,
    int_core_time_fail bigint DEFAULT 0 NOT NULL,
    int_frame_success_count integer DEFAULT 0 NOT NULL,
    int_frame_fail_count integer DEFAULT 0 NOT NULL,
    int_clock_time_fail integer DEFAULT 0 NOT NULL,
    int_clock_time_high integer DEFAULT 0 NOT NULL,
    int_clock_time_success integer DEFAULT 0 NOT NULL
);


--
-- Name: layer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer (
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    str_name character varying(256) NOT NULL,
    str_cmd character varying(4000) NOT NULL,
    str_range character varying(4000) NOT NULL,
    int_chunk_size bigint DEFAULT 1 NOT NULL,
    int_dispatch_order bigint DEFAULT 1 NOT NULL,
    int_cores_min bigint DEFAULT 100 NOT NULL,
    int_mem_min bigint DEFAULT 4194304 NOT NULL,
    str_tags character varying(4000) DEFAULT ''::character varying NOT NULL,
    str_type character varying(16) NOT NULL,
    b_threadable boolean DEFAULT true NOT NULL,
    str_services character varying(128) DEFAULT 'default'::character varying NOT NULL,
    b_optimize boolean DEFAULT true NOT NULL,
    int_cores_max integer DEFAULT 0 NOT NULL,
    int_gpu_min integer DEFAULT 0 NOT NULL
);


--
-- Name: layer_env; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_env (
    pk_layer_env character varying(36) NOT NULL,
    pk_layer character varying(36),
    pk_job character varying(36),
    str_key character varying(36),
    str_value character varying(2048)
);


--
-- Name: layer_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_history (
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    str_name character varying(512) NOT NULL,
    str_type character varying(16) NOT NULL,
    int_cores_min bigint DEFAULT 100 NOT NULL,
    int_mem_min bigint DEFAULT 4194304 NOT NULL,
    int_core_time_success bigint DEFAULT 0 NOT NULL,
    int_core_time_fail bigint DEFAULT 0 NOT NULL,
    int_frame_count bigint DEFAULT 0 NOT NULL,
    int_layer_count bigint DEFAULT 0 NOT NULL,
    int_waiting_count bigint DEFAULT 0 NOT NULL,
    int_dead_count bigint DEFAULT 0 NOT NULL,
    int_depend_count bigint DEFAULT 0 NOT NULL,
    int_eaten_count bigint DEFAULT 0 NOT NULL,
    int_succeeded_count bigint DEFAULT 0 NOT NULL,
    int_running_count bigint DEFAULT 0 NOT NULL,
    int_max_rss bigint DEFAULT 0 NOT NULL,
    b_archived boolean DEFAULT false NOT NULL,
    dt_last_modified date NOT NULL,
    str_services character varying(128)
);


--
-- Name: COLUMN layer_history.int_core_time_success; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.layer_history.int_core_time_success IS 'seconds per core succeeded';


--
-- Name: COLUMN layer_history.int_core_time_fail; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.layer_history.int_core_time_fail IS 'seconds per core failed';


--
-- Name: COLUMN layer_history.int_max_rss; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.layer_history.int_max_rss IS 'maximum kilobytes of rss memory used by a single frame';


--
-- Name: layer_mem; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_mem (
    pk_layer_mem character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    int_max_rss integer DEFAULT 0 NOT NULL,
    int_max_vss integer DEFAULT 0 NOT NULL
);


--
-- Name: layer_output; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_output (
    pk_layer_output character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    str_filespec character varying(2048) NOT NULL
);


--
-- Name: layer_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_resource (
    pk_layer_resource character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_cores bigint DEFAULT 0 NOT NULL,
    int_max_rss integer DEFAULT 0 NOT NULL,
    int_max_vss integer DEFAULT 0 NOT NULL
);


--
-- Name: layer_stat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_stat (
    pk_layer_stat character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_total_count bigint DEFAULT 0 NOT NULL,
    int_waiting_count bigint DEFAULT 0 NOT NULL,
    int_running_count bigint DEFAULT 0 NOT NULL,
    int_dead_count bigint DEFAULT 0 NOT NULL,
    int_depend_count bigint DEFAULT 0 NOT NULL,
    int_eaten_count bigint DEFAULT 0 NOT NULL,
    int_succeeded_count bigint DEFAULT 0 NOT NULL,
    int_checkpoint_count bigint DEFAULT 0 NOT NULL
);


--
-- Name: layer_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_usage (
    pk_layer_usage character varying(36) NOT NULL,
    pk_layer character varying(36) NOT NULL,
    pk_job character varying(36) NOT NULL,
    int_core_time_success bigint DEFAULT 0 NOT NULL,
    int_core_time_fail bigint DEFAULT 0 NOT NULL,
    int_frame_success_count integer DEFAULT 0 NOT NULL,
    int_frame_fail_count integer DEFAULT 0 NOT NULL,
    int_clock_time_fail integer DEFAULT 0 NOT NULL,
    int_clock_time_high integer DEFAULT 0 NOT NULL,
    int_clock_time_low integer DEFAULT 0 NOT NULL,
    int_clock_time_success integer DEFAULT 0 NOT NULL
);


--
-- Name: matcher; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matcher (
    pk_matcher character varying(36) NOT NULL,
    pk_filter character varying(36) NOT NULL,
    str_subject character varying(64) NOT NULL,
    str_match character varying(64) NOT NULL,
    str_value character varying(4000) NOT NULL,
    ts_created timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: matthew_stats_tab; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matthew_stats_tab (
    statid character varying(30),
    type character(1),
    version numeric,
    flags numeric,
    c1 character varying(30),
    c2 character varying(30),
    c3 character varying(30),
    c4 character varying(30),
    c5 character varying(30),
    n1 numeric,
    n2 numeric,
    n3 numeric,
    n4 numeric,
    n5 numeric,
    n6 numeric,
    n7 numeric,
    n8 numeric,
    n9 numeric,
    n10 numeric,
    n11 numeric,
    n12 numeric,
    d1 date,
    r1 bytea,
    r2 bytea,
    ch1 character varying(1000)
);


--
-- Name: owner; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.owner (
    pk_owner character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_username character varying(64) NOT NULL,
    ts_created timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_updated timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: point; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.point (
    pk_point character varying(36) NOT NULL,
    pk_dept character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_ti_task character varying(36),
    int_cores integer DEFAULT 0 NOT NULL,
    b_managed boolean DEFAULT false NOT NULL,
    int_min_cores integer DEFAULT 0 NOT NULL,
    float_tier numeric(16,2) DEFAULT 0 NOT NULL,
    ts_updated timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: proc; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc (
    pk_proc character varying(36) NOT NULL,
    pk_host character varying(36) NOT NULL,
    pk_job character varying(36),
    pk_show character varying(36),
    pk_layer character varying(36),
    pk_frame character varying(36),
    int_cores_reserved bigint NOT NULL,
    int_mem_reserved bigint NOT NULL,
    int_mem_used bigint DEFAULT 0 NOT NULL,
    int_mem_max_used bigint DEFAULT 0 NOT NULL,
    b_unbooked boolean DEFAULT false NOT NULL,
    int_mem_pre_reserved bigint DEFAULT 0 NOT NULL,
    int_virt_used integer DEFAULT 0 NOT NULL,
    int_virt_max_used integer DEFAULT 0 NOT NULL,
    str_redirect character varying(265),
    b_local boolean DEFAULT false NOT NULL,
    ts_ping timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_booked timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ts_dispatched timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    int_gpu_reserved integer DEFAULT 0 NOT NULL
);


--
-- Name: redirect; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.redirect (
    pk_proc character varying(36) NOT NULL,
    str_group_id character varying(36) NOT NULL,
    int_type bigint NOT NULL,
    str_destination_id character varying(512) NOT NULL,
    str_name character varying(512) NOT NULL,
    lng_creation_time bigint NOT NULL
);


--
-- Name: service; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service (
    pk_service character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_threadable boolean NOT NULL,
    int_cores_min integer NOT NULL,
    int_mem_min integer NOT NULL,
    str_tags character varying(128) NOT NULL,
    int_cores_max integer DEFAULT 0 NOT NULL,
    int_gpu_min integer DEFAULT 0 NOT NULL
);


--
-- Name: show; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.show (
    pk_show character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_paused boolean DEFAULT false NOT NULL,
    int_default_min_cores integer DEFAULT 100 NOT NULL,
    int_default_max_cores integer DEFAULT 10000 NOT NULL,
    int_frame_insert_count bigint DEFAULT 0 NOT NULL,
    int_job_insert_count bigint DEFAULT 0 NOT NULL,
    int_frame_success_count bigint DEFAULT 0 NOT NULL,
    int_frame_fail_count bigint DEFAULT 0 NOT NULL,
    b_booking_enabled boolean DEFAULT true NOT NULL,
    b_dispatch_enabled boolean DEFAULT true NOT NULL,
    b_active boolean DEFAULT true NOT NULL,
    str_comment_email character varying(1024)
);


--
-- Name: show_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.show_alias (
    pk_show_alias character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_name character varying(16) NOT NULL
);


--
-- Name: show_service; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.show_service (
    pk_show_service character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    b_threadable boolean NOT NULL,
    int_cores_min integer NOT NULL,
    int_mem_min integer NOT NULL,
    str_tags character varying(128) NOT NULL,
    int_cores_max integer DEFAULT 0 NOT NULL,
    int_gpu_min integer DEFAULT 0 NOT NULL
);


--
-- Name: sqln_explain_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sqln_explain_plan (
    statement_id character varying(30),
    "timestamp" date,
    remarks character varying(80),
    operation character varying(30),
    options character varying(30),
    object_node character varying(128),
    object_owner character varying(30),
    object_name character varying(30),
    object_instance bigint,
    object_type character varying(30),
    optimizer character varying(255),
    search_columns bigint,
    id bigint,
    parent_id bigint,
    "position" bigint,
    cost bigint,
    cardinality bigint,
    bytes bigint,
    other_tag character varying(255),
    partition_start character varying(255),
    partition_stop character varying(255),
    partition_id bigint,
    other text,
    distribution character varying(30)
);


--
-- Name: subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription (
    pk_subscription character varying(36) NOT NULL,
    pk_alloc character varying(36) NOT NULL,
    pk_show character varying(36) NOT NULL,
    int_size bigint DEFAULT 0 NOT NULL,
    int_burst bigint DEFAULT 0 NOT NULL,
    int_cores integer DEFAULT 0 NOT NULL,
    float_tier numeric(16,2) DEFAULT 0 NOT NULL
);


--
-- Name: task; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task (
    pk_task character varying(36) NOT NULL,
    pk_point character varying(36) NOT NULL,
    str_shot character varying(36) NOT NULL,
    int_min_cores integer DEFAULT 100 NOT NULL,
    int_adjust_cores integer DEFAULT 0 NOT NULL
);


--
-- Name: task_lock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_lock (
    pk_task_lock character varying(36) NOT NULL,
    str_name character varying(36) NOT NULL,
    int_lock bigint DEFAULT 0 NOT NULL,
    int_timeout bigint DEFAULT 30 NOT NULL,
    ts_lastrun timestamp(6) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: test; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test (
    col1 character varying(32)
);


--
-- Name: uncommitted_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uncommitted_transactions (
    inst_id numeric,
    sid numeric,
    serial numeric,
    username character varying(30),
    machine character varying(64),
    module character varying(48),
    service_name character varying(64),
    duration numeric,
    dt_recorded date DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: uncommitted_transactions_bak; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uncommitted_transactions_bak (
    inst_id numeric,
    sid numeric,
    serial numeric,
    username character varying(30),
    machine character varying(64),
    module character varying(48),
    service_name character varying(64),
    duration numeric,
    dt_recorded date
);


--
-- Name: v_history_frame; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_history_frame AS
 SELECT fh.pk_frame_history,
    fh.pk_frame,
    fh.pk_layer,
    fh.pk_job,
    fh.str_name,
    fh.str_state,
    fh.int_mem_reserved,
    fh.int_mem_max_used,
    fh.int_cores,
    fh.str_host,
    fh.int_exit_status,
    a.str_name AS str_alloc_name,
    a.b_billable AS b_alloc_billable,
    f.str_name AS str_facility_name,
    fh.int_ts_started,
    fh.int_ts_stopped,
    fh.int_checkpoint_count,
    NULL::text AS str_show_name,
    fh.dt_last_modified
   FROM (((public.frame_history fh
     JOIN public.job_history jh ON (((fh.pk_job)::text = (jh.pk_job)::text)))
     LEFT JOIN public.alloc a ON (((fh.pk_alloc)::text = (a.pk_alloc)::text)))
     LEFT JOIN public.facility f ON (((a.pk_facility)::text = (f.pk_facility)::text)))
  WHERE ((fh.dt_last_modified >= ( SELECT history_period.dt_begin
           FROM public.history_period)) AND (fh.dt_last_modified < ( SELECT history_period.dt_end
           FROM public.history_period)));


--
-- Name: v_history_job; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_history_job AS
 SELECT jh.pk_job,
    jh.str_name,
    jh.str_shot,
    jh.str_user,
    jh.int_core_time_success,
    jh.int_core_time_fail,
    jh.int_frame_count,
    jh.int_layer_count,
    jh.int_waiting_count,
    jh.int_dead_count,
    jh.int_depend_count,
    jh.int_eaten_count,
    jh.int_succeeded_count,
    jh.int_running_count,
    jh.int_max_rss,
    jh.b_archived,
    f.str_name AS str_facility_name,
    d.str_name AS str_dept_name,
    jh.int_ts_started,
    jh.int_ts_stopped,
    s.str_name AS str_show_name,
    jh.dt_last_modified
   FROM public.job_history jh,
    public.show s,
    public.facility f,
    public.dept d
  WHERE (((jh.pk_show)::text = (s.pk_show)::text) AND ((jh.pk_facility)::text = (f.pk_facility)::text) AND ((jh.pk_dept)::text = (d.pk_dept)::text) AND ((jh.dt_last_modified >= ( SELECT history_period.dt_begin
           FROM public.history_period)) OR (jh.int_ts_stopped = 0)));


--
-- Name: v_history_layer; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_history_layer AS
 SELECT lh.pk_layer,
    lh.pk_job,
    lh.str_name,
    lh.str_type,
    lh.int_cores_min,
    lh.int_mem_min,
    lh.int_core_time_success,
    lh.int_core_time_fail,
    lh.int_frame_count,
    lh.int_layer_count,
    lh.int_waiting_count,
    lh.int_dead_count,
    lh.int_depend_count,
    lh.int_eaten_count,
    lh.int_succeeded_count,
    lh.int_running_count,
    lh.int_max_rss,
    lh.b_archived,
    lh.str_services,
    s.str_name AS str_show_name,
    lh.dt_last_modified
   FROM public.layer_history lh,
    public.job_history jh,
    public.show s
  WHERE (((lh.pk_job)::text = (jh.pk_job)::text) AND ((jh.pk_show)::text = (s.pk_show)::text) AND (jh.dt_last_modified >= ( SELECT history_period.dt_begin
           FROM public.history_period)) AND (jh.dt_last_modified < ( SELECT history_period.dt_end
           FROM public.history_period)));


--
-- Name: v_temp; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_temp AS
 SELECT jh.pk_job,
    jh.str_name,
    jh.str_shot,
    jh.str_user,
    jh.int_core_time_success,
    jh.int_core_time_fail,
    jh.int_frame_count,
    jh.int_layer_count,
    jh.int_waiting_count,
    jh.int_dead_count,
    jh.int_depend_count,
    jh.int_eaten_count,
    jh.int_succeeded_count,
    jh.int_running_count,
    jh.int_max_rss,
    jh.b_archived,
    f.str_name AS str_facility_name,
    d.str_name AS str_dept_name,
    jh.int_ts_started,
    jh.int_ts_stopped,
    s.str_name AS str_show_name,
    jh.dt_last_modified
   FROM public.job_history jh,
    public.show s,
    public.facility f,
    public.dept d
  WHERE (((jh.pk_show)::text = (s.pk_show)::text) AND ((jh.pk_facility)::text = (f.pk_facility)::text) AND ((jh.pk_dept)::text = (d.pk_dept)::text) AND ((jh.pk_job)::text = ANY ((ARRAY['1514bafd-7d59-4974-b05c-d1a370366493'::character varying, 'eac9b6b6-d57b-472a-9a22-a6f4d0ec1a58'::character varying, 'ccb9740c-530f-4bce-94f0-493a78810d9d'::character varying, '7abd769f-289f-4ace-bc86-071a4c63f476'::character varying, '2170b154-104c-4e89-9ecc-05caf9112bbe'::character varying, '6f406088-0574-4d01-a774-61cff2ec0cf7'::character varying, '1f25d5a9-2637-4ecf-a0cf-3813fe3b9bcb'::character varying, '086d0d26-7553-408a-82b5-672fec1aa85f'::character varying, 'd00714d0-8c69-4ba5-a57b-f013638349ef'::character varying, '80d3de06-7b30-4cba-9033-e76be3fa3c98'::character varying, '9ef2c406-8cbb-4ff7-920d-2aa824bf368e'::character varying, 'fc6d2448-68b1-4035-bf65-3153a85ec5a1'::character varying, 'd431833c-6217-4955-a3fb-f7b7c41dca78'::character varying, '6c5c12cc-b878-4598-943e-72ac3eded01b'::character varying, '61f5b4a8-e688-40ef-824e-2659b3cfeae9'::character varying, '9c12b501-6180-4658-a849-92a8e2ac69c9'::character varying, '2599b44e-7257-478d-b75e-fd7a414d7c46'::character varying, '58cc47c5-e416-440e-bf61-11568d05741c'::character varying, 'dd214ab9-ba34-414c-b647-b739e08dde8a'::character varying, '607c35f0-9ac7-4375-8239-81cad9da9a99'::character varying, '73875446-a379-4128-8784-b74ba5ccd51f'::character varying, '4f29cbd5-bd82-4e94-bb67-f0f6a571884f'::character varying, '2a150e75-b446-4a17-88bf-9527b6d9a023'::character varying, '7742663f-8931-4b0a-a560-a95b40764017'::character varying, 'bec6160f-aed5-455c-88c1-b2d1b0225569'::character varying, '205c5a4c-b82e-4230-972c-671f70752bfa'::character varying, '8374b4e0-a6ff-4a33-ba17-33e508c396fb'::character varying, '5f866188-f8cc-4caa-8264-5b22e631bb25'::character varying, 'e7b99fb5-a45f-4ca7-beb6-cfc8a05d9ebe'::character varying, '5cf2eea4-52d8-4561-8f82-bd125a1089e9'::character varying, 'b9f0409c-0bac-4d80-91d5-4eca54ca8a29'::character varying, 'a0a1bfc1-c72e-4dae-ad83-16584c1fe37e'::character varying, '8c0c58f2-6384-4e87-ae4f-415cd23ccb5a'::character varying, 'abe2bd4f-a43e-4b32-88bf-3a73f5d503d5'::character varying, '97cc3df1-bfbe-4615-bdcd-b3ae65c8b2aa'::character varying, 'de2f00f6-8b5f-420d-835a-64e443828bc7'::character varying, 'c6158557-1370-4693-aa41-9de93788727a'::character varying, 'c81cc112-392e-4e92-95f4-d370993b0b4d'::character varying, 'e3f35fee-611d-4d47-bb96-789b3653382b'::character varying, '76a6df78-72d4-4ef8-9c2f-5237b005a8bd'::character varying, 'db1f7e0f-6ff2-4ebf-84d3-79d9bb898b4e'::character varying, 'f3bee9c0-8b6f-4ce1-b8c7-d7e8f07156e8'::character varying, '17c55582-ba72-4c8a-a089-5a5b8d099881'::character varying, '368ec111-b124-4206-b2f3-4698c99d2450'::character varying])::text[])));


--
-- Name: vs_alloc_usage; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_alloc_usage AS
 SELECT alloc.pk_alloc,
    COALESCE(sum(host.int_cores), (0)::numeric) AS int_cores,
    COALESCE(sum(host.int_cores_idle), (0)::numeric) AS int_idle_cores,
    COALESCE(sum((host.int_cores - host.int_cores_idle)), (0)::numeric) AS int_running_cores,
    COALESCE(( SELECT sum(host_1.int_cores) AS sum
           FROM public.host host_1
          WHERE (((host_1.pk_alloc)::text = (alloc.pk_alloc)::text) AND (((host_1.str_lock_state)::text = 'NimbyLocked'::text) OR ((host_1.str_lock_state)::text = 'Locked'::text)))), (0)::numeric) AS int_locked_cores,
    COALESCE(( SELECT sum(h.int_cores_idle) AS sum
           FROM public.host h,
            public.host_stat hs
          WHERE (((h.pk_host)::text = (hs.pk_host)::text) AND ((h.pk_alloc)::text = (alloc.pk_alloc)::text) AND ((h.str_lock_state)::text = 'Open'::text) AND ((hs.str_state)::text = 'Up'::text))), (0)::numeric) AS int_available_cores,
    count(host.pk_host) AS int_hosts,
    ( SELECT count(*) AS count
           FROM public.host host_1
          WHERE (((host_1.pk_alloc)::text = (alloc.pk_alloc)::text) AND ((host_1.str_lock_state)::text = 'Locked'::text))) AS int_locked_hosts,
    ( SELECT count(*) AS count
           FROM public.host h,
            public.host_stat hs
          WHERE (((h.pk_host)::text = (hs.pk_host)::text) AND ((h.pk_alloc)::text = (alloc.pk_alloc)::text) AND ((hs.str_state)::text = 'Down'::text))) AS int_down_hosts
   FROM (public.alloc
     LEFT JOIN public.host ON (((alloc.pk_alloc)::text = (host.pk_alloc)::text)))
  GROUP BY alloc.pk_alloc;


--
-- Name: vs_folder_counts; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_folder_counts AS
 SELECT folder.pk_folder,
    COALESCE(sum(job_stat.int_depend_count), (0)::numeric) AS int_depend_count,
    COALESCE(sum(job_stat.int_waiting_count), (0)::numeric) AS int_waiting_count,
    COALESCE(sum(job_stat.int_running_count), (0)::numeric) AS int_running_count,
    COALESCE(sum(job_stat.int_dead_count), (0)::numeric) AS int_dead_count,
    COALESCE(sum(job_resource.int_cores), (0)::numeric) AS int_cores,
    COALESCE(count(job.pk_job), (0)::bigint) AS int_job_count
   FROM (((public.folder
     LEFT JOIN public.job ON ((((folder.pk_folder)::text = (job.pk_folder)::text) AND ((job.str_state)::text = 'Pending'::text))))
     LEFT JOIN public.job_stat ON (((job.pk_job)::text = (job_stat.pk_job)::text)))
     LEFT JOIN public.job_resource ON (((job.pk_job)::text = (job_resource.pk_job)::text)))
  GROUP BY folder.pk_folder;


--
-- Name: vs_job_resource; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_job_resource AS
 SELECT job.pk_job,
    count(proc.pk_proc) AS int_procs,
    COALESCE(sum(proc.int_cores_reserved), (0)::numeric) AS int_cores,
    COALESCE(sum(proc.int_mem_reserved), (0)::numeric) AS int_mem_reserved
   FROM (public.job
     LEFT JOIN public.proc ON (((proc.pk_job)::text = (job.pk_job)::text)))
  GROUP BY job.pk_job;


--
-- Name: vs_show_resource; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_show_resource AS
 SELECT job.pk_show,
    sum(job_resource.int_cores) AS int_cores
   FROM public.job,
    public.job_resource
  WHERE (((job.pk_job)::text = (job_resource.pk_job)::text) AND ((job.str_state)::text = 'Pending'::text))
  GROUP BY job.pk_show;


--
-- Name: vs_show_stat; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_show_stat AS
 SELECT job.pk_show,
    sum((job_stat.int_waiting_count + job_stat.int_depend_count)) AS int_pending_count,
    sum(job_stat.int_running_count) AS int_running_count,
    sum(job_stat.int_dead_count) AS int_dead_count,
    count(1) AS int_job_count
   FROM public.job_stat,
    public.job
  WHERE (((job_stat.pk_job)::text = (job.pk_job)::text) AND ((job.str_state)::text = 'Pending'::text))
  GROUP BY job.pk_show;


--
-- Name: vs_waiting; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vs_waiting AS
 SELECT job.pk_show
   FROM public.job_resource jr,
    public.job_stat,
    public.job
  WHERE (((job_stat.pk_job)::text = (job.pk_job)::text) AND ((jr.pk_job)::text = (job.pk_job)::text) AND ((job.str_state)::text = 'Pending'::text) AND (job.b_paused = false) AND ((jr.int_max_cores - jr.int_cores) >= 100) AND (job_stat.int_waiting_count <> 0))
  GROUP BY job.pk_show;


--
-- Name: action c_action_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action
    ADD CONSTRAINT c_action_pk PRIMARY KEY (pk_action);


--
-- Name: alloc c_alloc_name_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alloc
    ADD CONSTRAINT c_alloc_name_uniq UNIQUE (str_name);


--
-- Name: alloc c_alloc_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alloc
    ADD CONSTRAINT c_alloc_pk PRIMARY KEY (pk_alloc);


--
-- Name: comments c_comment_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT c_comment_pk PRIMARY KEY (pk_comment);


--
-- Name: depend c_depend_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.depend
    ADD CONSTRAINT c_depend_pk PRIMARY KEY (pk_depend);


--
-- Name: dept c_dept_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dept
    ADD CONSTRAINT c_dept_pk PRIMARY KEY (pk_dept);


--
-- Name: facility c_facility_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility
    ADD CONSTRAINT c_facility_pk PRIMARY KEY (pk_facility);


--
-- Name: filter c_filter_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.filter
    ADD CONSTRAINT c_filter_pk PRIMARY KEY (pk_filter);


--
-- Name: folder_level c_folder_level_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_level
    ADD CONSTRAINT c_folder_level_pk PRIMARY KEY (pk_folder_level);


--
-- Name: folder_level c_folder_level_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_level
    ADD CONSTRAINT c_folder_level_uk UNIQUE (pk_folder);


--
-- Name: folder c_folder_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT c_folder_pk PRIMARY KEY (pk_folder);


--
-- Name: folder_resource c_folder_resource_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_resource
    ADD CONSTRAINT c_folder_resource_pk PRIMARY KEY (pk_folder_resource);


--
-- Name: folder c_folder_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT c_folder_uk UNIQUE (pk_parent_folder, str_name);


--
-- Name: frame_history c_frame_history_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame_history
    ADD CONSTRAINT c_frame_history_pk PRIMARY KEY (pk_frame_history);


--
-- Name: frame c_frame_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame
    ADD CONSTRAINT c_frame_pk PRIMARY KEY (pk_frame);


--
-- Name: frame c_frame_str_name_unq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame
    ADD CONSTRAINT c_frame_str_name_unq UNIQUE (str_name, pk_job);


--
-- Name: history_period c_history_period_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.history_period
    ADD CONSTRAINT c_history_period_pk PRIMARY KEY (pk);


--
-- Name: host c_host_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host
    ADD CONSTRAINT c_host_pk PRIMARY KEY (pk_host);


--
-- Name: host_stat c_host_stat_pk_host_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_stat
    ADD CONSTRAINT c_host_stat_pk_host_uk UNIQUE (pk_host);


--
-- Name: host_tag c_host_tag_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_tag
    ADD CONSTRAINT c_host_tag_pk PRIMARY KEY (pk_host_tag);


--
-- Name: host c_host_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host
    ADD CONSTRAINT c_host_uk UNIQUE (str_name);


--
-- Name: host_stat c_hoststat_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_stat
    ADD CONSTRAINT c_hoststat_pk PRIMARY KEY (pk_host_stat);


--
-- Name: job_env c_job_env_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_env
    ADD CONSTRAINT c_job_env_pk PRIMARY KEY (pk_job_env);


--
-- Name: job_history c_job_history_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_history
    ADD CONSTRAINT c_job_history_pk PRIMARY KEY (pk_job);


--
-- Name: job_mem c_job_mem_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_mem
    ADD CONSTRAINT c_job_mem_pk PRIMARY KEY (pk_job_mem);


--
-- Name: job c_job_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_pk PRIMARY KEY (pk_job);


--
-- Name: job_post c_job_post_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_post
    ADD CONSTRAINT c_job_post_pk PRIMARY KEY (pk_job_post);


--
-- Name: job_resource c_job_resource_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_resource
    ADD CONSTRAINT c_job_resource_pk PRIMARY KEY (pk_job_resource);


--
-- Name: job_resource c_job_resource_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_resource
    ADD CONSTRAINT c_job_resource_uk UNIQUE (pk_job);


--
-- Name: job_stat c_job_stat_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_stat
    ADD CONSTRAINT c_job_stat_pk PRIMARY KEY (pk_job_stat);


--
-- Name: job c_job_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_uk UNIQUE (str_visible_name);


--
-- Name: job_usage c_job_usage_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_usage
    ADD CONSTRAINT c_job_usage_pk PRIMARY KEY (pk_job_usage);


--
-- Name: job_usage c_job_usage_pk_job_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_usage
    ADD CONSTRAINT c_job_usage_pk_job_uniq UNIQUE (pk_job);


--
-- Name: layer_env c_layer_env_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_env
    ADD CONSTRAINT c_layer_env_pk PRIMARY KEY (pk_layer_env);


--
-- Name: layer_history c_layer_history_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_history
    ADD CONSTRAINT c_layer_history_pk PRIMARY KEY (pk_layer);


--
-- Name: layer_mem c_layer_mem_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_mem
    ADD CONSTRAINT c_layer_mem_pk PRIMARY KEY (pk_layer_mem);


--
-- Name: layer c_layer_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT c_layer_pk PRIMARY KEY (pk_layer);


--
-- Name: layer c_layer_str_name_unq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT c_layer_str_name_unq UNIQUE (str_name, pk_job);


--
-- Name: layer_usage c_layer_usage_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_usage
    ADD CONSTRAINT c_layer_usage_pk PRIMARY KEY (pk_layer_usage);


--
-- Name: layer_usage c_layer_usage_pk_layer_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_usage
    ADD CONSTRAINT c_layer_usage_pk_layer_uk UNIQUE (pk_layer);


--
-- Name: layer_resource c_layerresource_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_resource
    ADD CONSTRAINT c_layerresource_pk PRIMARY KEY (pk_layer_resource);


--
-- Name: layer_resource c_layerresource_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_resource
    ADD CONSTRAINT c_layerresource_uk UNIQUE (pk_layer);


--
-- Name: layer_stat c_layerstat_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_stat
    ADD CONSTRAINT c_layerstat_pk PRIMARY KEY (pk_layer_stat);


--
-- Name: matcher c_matcher_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matcher
    ADD CONSTRAINT c_matcher_pk PRIMARY KEY (pk_matcher);


--
-- Name: deed c_pk_deed; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deed
    ADD CONSTRAINT c_pk_deed PRIMARY KEY (pk_deed);


--
-- Name: host_local c_pk_host_local; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_local
    ADD CONSTRAINT c_pk_host_local PRIMARY KEY (pk_host_local);


--
-- Name: job_local c_pk_job_local; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_local
    ADD CONSTRAINT c_pk_job_local PRIMARY KEY (pk_job_local);


--
-- Name: layer_output c_pk_layer_output; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_output
    ADD CONSTRAINT c_pk_layer_output PRIMARY KEY (pk_layer_output);


--
-- Name: owner c_pk_owner; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner
    ADD CONSTRAINT c_pk_owner PRIMARY KEY (pk_owner);


--
-- Name: config c_pk_pkconfig; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT c_pk_pkconfig PRIMARY KEY (pk_config);


--
-- Name: service c_pk_service; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service
    ADD CONSTRAINT c_pk_service PRIMARY KEY (pk_service);


--
-- Name: show_service c_pk_show_service; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.show_service
    ADD CONSTRAINT c_pk_show_service PRIMARY KEY (pk_show_service);


--
-- Name: point c_point_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.point
    ADD CONSTRAINT c_point_pk PRIMARY KEY (pk_point);


--
-- Name: point c_point_pk_show_dept; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.point
    ADD CONSTRAINT c_point_pk_show_dept UNIQUE (pk_show, pk_dept);


--
-- Name: proc c_proc_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc
    ADD CONSTRAINT c_proc_pk PRIMARY KEY (pk_proc);


--
-- Name: proc c_proc_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc
    ADD CONSTRAINT c_proc_uk UNIQUE (pk_frame);


--
-- Name: redirect c_redirect_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.redirect
    ADD CONSTRAINT c_redirect_pk PRIMARY KEY (pk_proc);


--
-- Name: show_alias c_show_alias_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.show_alias
    ADD CONSTRAINT c_show_alias_pk PRIMARY KEY (pk_show_alias);


--
-- Name: show c_show_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.show
    ADD CONSTRAINT c_show_pk PRIMARY KEY (pk_show);


--
-- Name: config c_show_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT c_show_uk UNIQUE (str_key);


--
-- Name: host c_str_host_fqdn_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host
    ADD CONSTRAINT c_str_host_fqdn_uk UNIQUE (str_fqdn);


--
-- Name: subscription c_subscription_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT c_subscription_pk PRIMARY KEY (pk_subscription);


--
-- Name: subscription c_subscription_uk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT c_subscription_uk UNIQUE (pk_show, pk_alloc);


--
-- Name: task_lock c_task_lock_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_lock
    ADD CONSTRAINT c_task_lock_pk PRIMARY KEY (pk_task_lock);


--
-- Name: task c_task_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT c_task_pk PRIMARY KEY (pk_task);


--
-- Name: task c_task_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT c_task_uniq UNIQUE (str_shot, pk_point);


--
-- Name: flyway_schema_history flyway_schema_history_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flyway_schema_history
    ADD CONSTRAINT flyway_schema_history_pk PRIMARY KEY (installed_rank);


--
-- Name: flyway_schema_history_s_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX flyway_schema_history_s_idx ON public.flyway_schema_history USING btree (success);


--
-- Name: i_action_pk_filter; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_action_pk_filter ON public.action USING btree (pk_filter);


--
-- Name: i_action_pk_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_action_pk_group ON public.action USING btree (pk_folder);


--
-- Name: i_alloc_pk_facility; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_alloc_pk_facility ON public.alloc USING btree (pk_facility);


--
-- Name: i_booking_3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_booking_3 ON public.job USING btree (str_state, b_paused, pk_show, pk_facility);


--
-- Name: i_comment_pk_host; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_comment_pk_host ON public.comments USING btree (pk_host);


--
-- Name: i_comment_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_comment_pk_job ON public.comments USING btree (pk_job);


--
-- Name: i_deed_pk_host; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_deed_pk_host ON public.deed USING btree (pk_host);


--
-- Name: i_deed_pk_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_deed_pk_owner ON public.deed USING btree (pk_owner);


--
-- Name: i_depend_b_composite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_b_composite ON public.depend USING btree (b_composite);


--
-- Name: i_depend_er_frame; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_er_frame ON public.depend USING btree (pk_frame_depend_er);


--
-- Name: i_depend_er_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_er_layer ON public.depend USING btree (pk_layer_depend_er);


--
-- Name: i_depend_on_frame; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_on_frame ON public.depend USING btree (pk_frame_depend_on);


--
-- Name: i_depend_on_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_on_layer ON public.depend USING btree (pk_layer_depend_on);


--
-- Name: i_depend_pk_er_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_pk_er_job ON public.depend USING btree (pk_job_depend_er);


--
-- Name: i_depend_pk_on_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_pk_on_job ON public.depend USING btree (pk_job_depend_on);


--
-- Name: i_depend_pkparent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_pkparent ON public.depend USING btree (pk_parent);


--
-- Name: i_depend_signature; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_depend_signature ON public.depend USING btree (str_signature);


--
-- Name: i_depend_str_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_str_target ON public.depend USING btree (str_target);


--
-- Name: i_depend_str_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_depend_str_type ON public.depend USING btree (str_type);


--
-- Name: i_filters_pk_show; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_filters_pk_show ON public.filter USING btree (pk_show);


--
-- Name: i_folder_pkparentfolder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folder_pkparentfolder ON public.folder USING btree (pk_parent_folder);


--
-- Name: i_folder_pkshow; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folder_pkshow ON public.folder USING btree (pk_show);


--
-- Name: i_folder_res_int_max_cores; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folder_res_int_max_cores ON public.folder_resource USING btree (int_max_cores);


--
-- Name: i_folder_resource_fl_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folder_resource_fl_tier ON public.folder_resource USING btree (float_tier);


--
-- Name: i_folder_strname; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folder_strname ON public.folder USING btree (str_name);


--
-- Name: i_folderresource_pkfolder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_folderresource_pkfolder ON public.folder_resource USING btree (pk_folder);


--
-- Name: i_frame_dispatch_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_dispatch_idx ON public.frame USING btree (int_dispatch_order, int_layer_order);


--
-- Name: i_frame_history_int_exit_stat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_int_exit_stat ON public.frame_history USING btree (int_exit_status);


--
-- Name: i_frame_history_int_ts_stopped; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_int_ts_stopped ON public.frame_history USING btree (int_ts_stopped);


--
-- Name: i_frame_history_pk_alloc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_pk_alloc ON public.frame_history USING btree (pk_alloc);


--
-- Name: i_frame_history_pk_frame; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_pk_frame ON public.frame_history USING btree (pk_frame);


--
-- Name: i_frame_history_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_pk_job ON public.frame_history USING btree (pk_job);


--
-- Name: i_frame_history_pk_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_pk_layer ON public.frame_history USING btree (pk_layer);


--
-- Name: i_frame_history_str_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_str_state ON public.frame_history USING btree (str_state);


--
-- Name: i_frame_history_ts_start_stop; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_history_ts_start_stop ON public.frame_history USING btree (int_ts_started, int_ts_stopped);


--
-- Name: i_frame_int_gpu_reserved; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_int_gpu_reserved ON public.frame USING btree (int_gpu_reserved);


--
-- Name: i_frame_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_pk_job ON public.frame USING btree (pk_job);


--
-- Name: i_frame_pkjoblayer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_pkjoblayer ON public.frame USING btree (pk_layer);


--
-- Name: i_frame_state_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_frame_state_job ON public.frame USING btree (str_state, pk_job);


--
-- Name: i_host_int_gpu; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_int_gpu ON public.host USING btree (int_gpu);


--
-- Name: i_host_int_gpu_idle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_int_gpu_idle ON public.host USING btree (int_gpu_idle);


--
-- Name: i_host_local; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_local ON public.host_local USING btree (pk_host);


--
-- Name: i_host_local_int_gpu_idle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_local_int_gpu_idle ON public.host_local USING btree (int_gpu_idle);


--
-- Name: i_host_local_int_gpu_max; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_local_int_gpu_max ON public.host_local USING btree (int_gpu_max);


--
-- Name: i_host_local_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_local_pk_job ON public.host_local USING btree (pk_job);


--
-- Name: i_host_local_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_host_local_unique ON public.host_local USING btree (pk_host, pk_job);


--
-- Name: i_host_pkalloc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_pkalloc ON public.host USING btree (pk_alloc);


--
-- Name: i_host_stat_int_gpu_free; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_stat_int_gpu_free ON public.host_stat USING btree (int_gpu_free);


--
-- Name: i_host_stat_int_gpu_total; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_stat_int_gpu_total ON public.host_stat USING btree (int_gpu_total);


--
-- Name: i_host_stat_str_os; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_stat_str_os ON public.host_stat USING btree (str_os);


--
-- Name: i_host_str_tag_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_str_tag_type ON public.host_tag USING btree (str_tag_type);


--
-- Name: i_host_str_tags; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_str_tags ON public.host USING btree (str_tags);


--
-- Name: i_host_strlockstate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_strlockstate ON public.host USING btree (str_lock_state);


--
-- Name: i_host_tag_pk_host; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_host_tag_pk_host ON public.host_tag USING btree (pk_host);


--
-- Name: i_job_env_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_env_pk_job ON public.job_env USING btree (pk_job);


--
-- Name: i_job_history_b_archived; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_b_archived ON public.job_history USING btree (b_archived);


--
-- Name: i_job_history_pk_dept; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_pk_dept ON public.job_history USING btree (pk_dept);


--
-- Name: i_job_history_pk_facility; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_pk_facility ON public.job_history USING btree (pk_facility);


--
-- Name: i_job_history_pk_show; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_pk_show ON public.job_history USING btree (pk_show);


--
-- Name: i_job_history_str_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_str_name ON public.job_history USING btree (str_name);


--
-- Name: i_job_history_str_shot; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_str_shot ON public.job_history USING btree (str_shot);


--
-- Name: i_job_history_str_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_str_user ON public.job_history USING btree (str_user);


--
-- Name: i_job_history_ts_start_stop; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_history_ts_start_stop ON public.job_history USING btree (int_ts_started, int_ts_stopped);


--
-- Name: i_job_local_pk_host; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_job_local_pk_host ON public.job_local USING btree (pk_host);


--
-- Name: i_job_local_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_job_local_pk_job ON public.job_local USING btree (pk_job);


--
-- Name: i_job_mem_int_max_rss; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_mem_int_max_rss ON public.job_mem USING btree (int_max_rss);


--
-- Name: i_job_mem_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_job_mem_pk_job ON public.job_mem USING btree (pk_job);


--
-- Name: i_job_pk_dept; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_pk_dept ON public.job USING btree (pk_dept);


--
-- Name: i_job_pk_facility; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_pk_facility ON public.job USING btree (pk_facility);


--
-- Name: i_job_pkgroup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_pkgroup ON public.job USING btree (pk_folder);


--
-- Name: i_job_pkshow; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_pkshow ON public.job USING btree (pk_show);


--
-- Name: i_job_post_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_post_pk_job ON public.job_post USING btree (pk_job);


--
-- Name: i_job_post_pk_post_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_post_pk_post_job ON public.job_post USING btree (pk_post_job);


--
-- Name: i_job_resource_cores; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_resource_cores ON public.job_resource USING btree (int_cores);


--
-- Name: i_job_resource_max_c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_resource_max_c ON public.job_resource USING btree (int_max_cores);


--
-- Name: i_job_resource_min_max; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_resource_min_max ON public.job_resource USING btree (int_min_cores, int_max_cores);


--
-- Name: i_job_stat_int_waiting_count; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_stat_int_waiting_count ON public.job_stat USING btree (int_waiting_count);


--
-- Name: i_job_stat_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_job_stat_pk_job ON public.job_stat USING btree (pk_job);


--
-- Name: i_job_str_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_str_name ON public.job USING btree (str_name);


--
-- Name: i_job_str_os; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_str_os ON public.job USING btree (str_os);


--
-- Name: i_job_str_shot; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_str_shot ON public.job USING btree (str_shot);


--
-- Name: i_job_str_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_str_state ON public.job USING btree (str_state);


--
-- Name: i_job_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_job_tier ON public.job_resource USING btree (float_tier);


--
-- Name: i_layer_b_threadable; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_b_threadable ON public.layer USING btree (b_threadable);


--
-- Name: i_layer_cores_mem; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_cores_mem ON public.layer USING btree (int_cores_min, int_mem_min);


--
-- Name: i_layer_cores_mem_thread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_cores_mem_thread ON public.layer USING btree (int_cores_min, int_mem_min, b_threadable);


--
-- Name: i_layer_env_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_env_pk_job ON public.layer_env USING btree (pk_job);


--
-- Name: i_layer_env_pk_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_env_pk_layer ON public.layer_env USING btree (pk_layer);


--
-- Name: i_layer_history_b_archived; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_history_b_archived ON public.layer_history USING btree (b_archived);


--
-- Name: i_layer_history_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_history_pk_job ON public.layer_history USING btree (pk_job);


--
-- Name: i_layer_history_str_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_history_str_name ON public.layer_history USING btree (str_name);


--
-- Name: i_layer_history_str_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_history_str_type ON public.layer_history USING btree (str_type);


--
-- Name: i_layer_int_dispatch_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_int_dispatch_order ON public.layer USING btree (int_dispatch_order);


--
-- Name: i_layer_int_gpu_min; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_int_gpu_min ON public.layer USING btree (int_gpu_min);


--
-- Name: i_layer_mem_int_max_rss; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_mem_int_max_rss ON public.layer_mem USING btree (int_max_rss);


--
-- Name: i_layer_mem_min; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_mem_min ON public.layer USING btree (int_mem_min);


--
-- Name: i_layer_mem_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_mem_pk_job ON public.layer_mem USING btree (pk_job);


--
-- Name: i_layer_mem_pk_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_layer_mem_pk_layer ON public.layer_mem USING btree (pk_layer);


--
-- Name: i_layer_output_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_output_pk_job ON public.layer_output USING btree (pk_job);


--
-- Name: i_layer_output_pk_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_output_pk_layer ON public.layer_output USING btree (pk_layer);


--
-- Name: i_layer_output_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_layer_output_unique ON public.layer_output USING btree (pk_layer, str_filespec);


--
-- Name: i_layer_pkjob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_pkjob ON public.layer USING btree (pk_job);


--
-- Name: i_layer_resource_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_resource_pk_job ON public.layer_resource USING btree (pk_job);


--
-- Name: i_layer_stat_pk_layer; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_layer_stat_pk_layer ON public.layer_stat USING btree (pk_layer);


--
-- Name: i_layer_strname; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_strname ON public.layer USING btree (str_name);


--
-- Name: i_layer_usage_pk_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layer_usage_pk_job ON public.layer_usage USING btree (pk_job);


--
-- Name: i_layerstat_int_waiting_count; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layerstat_int_waiting_count ON public.layer_stat USING btree ((
CASE
    WHEN (int_waiting_count > 0) THEN 1
    ELSE NULL::integer
END), (
CASE
    WHEN (int_waiting_count > 0) THEN pk_layer
    ELSE NULL::character varying
END));


--
-- Name: i_layerstat_pkjob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_layerstat_pkjob ON public.layer_stat USING btree (pk_job);


--
-- Name: i_matcher_pk_filter; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_matcher_pk_filter ON public.matcher USING btree (pk_filter);


--
-- Name: i_matthew_stats_tab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_matthew_stats_tab ON public.matthew_stats_tab USING btree (statid, type, c5, c1, c2, c3, c4, version);


--
-- Name: i_owner_pk_show; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_owner_pk_show ON public.owner USING btree (pk_show);


--
-- Name: i_owner_str_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_owner_str_username ON public.owner USING btree (str_username);


--
-- Name: i_point_pk_dept; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_point_pk_dept ON public.point USING btree (pk_dept);


--
-- Name: i_point_pk_show; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_point_pk_show ON public.point USING btree (pk_show);


--
-- Name: i_point_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_point_tier ON public.point USING btree (float_tier);


--
-- Name: i_proc_int_gpu_reserved; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_proc_int_gpu_reserved ON public.proc USING btree (int_gpu_reserved);


--
-- Name: i_proc_pkhost; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_proc_pkhost ON public.proc USING btree (pk_host);


--
-- Name: i_proc_pkjob; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_proc_pkjob ON public.proc USING btree (pk_job);


--
-- Name: i_proc_pklayer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_proc_pklayer ON public.proc USING btree (pk_layer);


--
-- Name: i_proc_pkshow; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_proc_pkshow ON public.proc USING btree (pk_show);


--
-- Name: i_redirect_create; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_redirect_create ON public.redirect USING btree (lng_creation_time);


--
-- Name: i_redirect_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_redirect_group ON public.redirect USING btree (str_group_id);


--
-- Name: i_service_int_gpu_min; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_service_int_gpu_min ON public.service USING btree (int_gpu_min);


--
-- Name: i_service_str_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_service_str_name ON public.service USING btree (str_name);


--
-- Name: i_show_alias_pk_show; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_show_alias_pk_show ON public.show_alias USING btree (pk_show);


--
-- Name: i_show_service_int_gpu_min; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_show_service_int_gpu_min ON public.show_service USING btree (int_gpu_min);


--
-- Name: i_show_service_str_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX i_show_service_str_name ON public.show_service USING btree (str_name, pk_show);


--
-- Name: i_sub_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_sub_tier ON public.subscription USING btree (float_tier);


--
-- Name: i_subscription_pkalloc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_subscription_pkalloc ON public.subscription USING btree (pk_alloc);


--
-- Name: i_task_pk_point; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX i_task_pk_point ON public.task USING btree (pk_point);


--
-- Name: folder after_insert_folder; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_insert_folder AFTER INSERT ON public.folder FOR EACH ROW EXECUTE PROCEDURE public.trigger__after_insert_folder();


--
-- Name: job after_insert_job; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_insert_job AFTER INSERT ON public.job FOR EACH ROW EXECUTE PROCEDURE public.trigger__after_insert_job();


--
-- Name: layer after_insert_layer; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_insert_layer AFTER INSERT ON public.layer FOR EACH ROW EXECUTE PROCEDURE public.trigger__after_insert_layer();


--
-- Name: job after_job_dept_update; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_job_dept_update AFTER UPDATE ON public.job FOR EACH ROW WHEN ((((new.pk_dept)::text <> (old.pk_dept)::text) AND ((new.str_state)::text = 'Pending'::text))) EXECUTE PROCEDURE public.trigger__after_job_dept_update();


--
-- Name: job after_job_finished; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_job_finished AFTER UPDATE ON public.job FOR EACH ROW WHEN ((((old.str_state)::text = 'Pending'::text) AND ((new.str_state)::text = 'Finished'::text))) EXECUTE PROCEDURE public.trigger__after_job_finished();


--
-- Name: job after_job_moved; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER after_job_moved AFTER UPDATE ON public.job FOR EACH ROW WHEN (((new.pk_folder)::text <> (old.pk_folder)::text)) EXECUTE PROCEDURE public.trigger__after_job_moved();


--
-- Name: folder before_delete_folder; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_delete_folder BEFORE DELETE ON public.folder FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_delete_folder();


--
-- Name: host before_delete_host; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_delete_host BEFORE DELETE ON public.host FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_delete_host();


--
-- Name: job before_delete_job; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_delete_job BEFORE DELETE ON public.job FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_delete_job();


--
-- Name: layer before_delete_layer; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_delete_layer BEFORE DELETE ON public.layer FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_delete_layer();


--
-- Name: folder before_insert_folder; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_insert_folder BEFORE INSERT ON public.folder FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_insert_folder();


--
-- Name: proc before_insert_proc; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_insert_proc BEFORE INSERT ON public.proc FOR EACH ROW EXECUTE PROCEDURE public.trigger__before_insert_proc();


--
-- Name: frame frame_history_open; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER frame_history_open AFTER UPDATE ON public.frame FOR EACH ROW WHEN (((new.str_state)::text <> (old.str_state)::text)) EXECUTE PROCEDURE public.trigger__frame_history_open();


--
-- Name: point point_tier; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER point_tier BEFORE UPDATE ON public.point FOR EACH ROW EXECUTE PROCEDURE public.trigger__point_tier();


--
-- Name: frame_history tbiu_frame_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tbiu_frame_history BEFORE INSERT OR UPDATE ON public.frame_history FOR EACH ROW EXECUTE PROCEDURE public.trigger__tbiu_frame_history();


--
-- Name: job_history tbiu_job_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tbiu_job_history BEFORE INSERT OR UPDATE ON public.job_history FOR EACH ROW EXECUTE PROCEDURE public.trigger__tbiu_job_history();


--
-- Name: layer_history tbiu_layer_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tbiu_layer_history BEFORE INSERT OR UPDATE ON public.layer_history FOR EACH ROW EXECUTE PROCEDURE public.trigger__tbiu_layer_history();


--
-- Name: folder_resource tier_folder; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tier_folder BEFORE UPDATE ON public.folder_resource FOR EACH ROW EXECUTE PROCEDURE public.trigger__tier_folder();


--
-- Name: host_local tier_host_local; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tier_host_local BEFORE UPDATE ON public.host_local FOR EACH ROW EXECUTE PROCEDURE public.trigger__tier_host_local();


--
-- Name: job_resource tier_job; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tier_job BEFORE UPDATE ON public.job_resource FOR EACH ROW EXECUTE PROCEDURE public.trigger__tier_job();


--
-- Name: subscription tier_subscription; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tier_subscription BEFORE UPDATE ON public.subscription FOR EACH ROW EXECUTE PROCEDURE public.trigger__tier_subscription();


--
-- Name: frame update_frame_checkpoint_state; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_frame_checkpoint_state BEFORE UPDATE ON public.frame FOR EACH ROW WHEN ((((new.str_state)::text = 'Waiting'::text) AND ((old.str_state)::text = 'Running'::text) AND ((new.str_checkpoint_state)::text = ANY ((ARRAY['Enabled'::character varying, 'Copying'::character varying])::text[])))) EXECUTE PROCEDURE public.trigger__update_frame_checkpoint_state();


--
-- Name: frame update_frame_dep_to_wait; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_frame_dep_to_wait BEFORE UPDATE ON public.frame FOR EACH ROW WHEN (((old.int_depend_count > 0) AND (new.int_depend_count < 1) AND ((old.str_state)::text = 'Depend'::text))) EXECUTE PROCEDURE public.trigger__update_frame_dep_to_wait();


--
-- Name: frame update_frame_eaten; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_frame_eaten BEFORE UPDATE ON public.frame FOR EACH ROW WHEN ((((new.str_state)::text = 'Eaten'::text) AND ((old.str_state)::text = 'Succeeded'::text))) EXECUTE PROCEDURE public.trigger__update_frame_eaten();


--
-- Name: frame update_frame_status_counts; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_frame_status_counts AFTER UPDATE ON public.frame FOR EACH ROW WHEN ((((old.str_state)::text <> 'Setup'::text) AND ((old.str_state)::text <> (new.str_state)::text))) EXECUTE PROCEDURE public.trigger__update_frame_status_counts();


--
-- Name: frame update_frame_wait_to_dep; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_frame_wait_to_dep BEFORE UPDATE ON public.frame FOR EACH ROW WHEN (((new.int_depend_count > 0) AND ((new.str_state)::text = ANY ((ARRAY['Dead'::character varying, 'Succeeded'::character varying, 'Waiting'::character varying, 'Checkpoint'::character varying])::text[])))) EXECUTE PROCEDURE public.trigger__update_frame_wait_to_dep();


--
-- Name: proc update_proc_update_layer; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_proc_update_layer AFTER UPDATE ON public.proc FOR EACH ROW WHEN (((new.pk_layer)::text <> (old.pk_layer)::text)) EXECUTE PROCEDURE public.trigger__update_proc_update_layer();


--
-- Name: proc upgrade_proc_memory_usage; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER upgrade_proc_memory_usage AFTER UPDATE ON public.proc FOR EACH ROW WHEN ((new.int_mem_reserved <> old.int_mem_reserved)) EXECUTE PROCEDURE public.trigger__upgrade_proc_memory_usage();


--
-- Name: host_local verify_host_local; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER verify_host_local BEFORE UPDATE ON public.host_local FOR EACH ROW WHEN (((new.int_cores_max = old.int_cores_max) AND (new.int_mem_max = old.int_mem_max) AND ((new.int_cores_idle <> old.int_cores_idle) OR (new.int_mem_idle <> old.int_mem_idle)))) EXECUTE PROCEDURE public.trigger__verify_host_local();


--
-- Name: host verify_host_resources; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER verify_host_resources BEFORE UPDATE ON public.host FOR EACH ROW WHEN (((new.int_cores_idle <> old.int_cores_idle) OR (new.int_mem_idle <> old.int_mem_idle))) EXECUTE PROCEDURE public.trigger__verify_host_resources();


--
-- Name: job_local verify_job_local; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER verify_job_local BEFORE UPDATE ON public.job_local FOR EACH ROW WHEN (((new.int_max_cores = old.int_max_cores) AND (new.int_cores > old.int_cores))) EXECUTE PROCEDURE public.trigger__verify_job_local();


--
-- Name: job_resource verify_job_resources; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER verify_job_resources BEFORE UPDATE ON public.job_resource FOR EACH ROW WHEN (((new.int_max_cores = old.int_max_cores) AND (new.int_cores > old.int_cores))) EXECUTE PROCEDURE public.trigger__verify_job_resources();


--
-- Name: subscription verify_subscription; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER verify_subscription BEFORE UPDATE ON public.subscription FOR EACH ROW WHEN (((new.int_burst = old.int_burst) AND (new.int_cores > old.int_cores))) EXECUTE PROCEDURE public.trigger__verify_subscription();


--
-- Name: action c_action_pk_filter; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action
    ADD CONSTRAINT c_action_pk_filter FOREIGN KEY (pk_filter) REFERENCES public.filter(pk_filter);


--
-- Name: action c_action_pk_folder; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action
    ADD CONSTRAINT c_action_pk_folder FOREIGN KEY (pk_folder) REFERENCES public.folder(pk_folder);


--
-- Name: alloc c_alloc_pk_facility; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alloc
    ADD CONSTRAINT c_alloc_pk_facility FOREIGN KEY (pk_facility) REFERENCES public.facility(pk_facility);


--
-- Name: comments c_comment_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT c_comment_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: comments c_comment_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT c_comment_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: deed c_deed_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deed
    ADD CONSTRAINT c_deed_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: filter c_filter_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.filter
    ADD CONSTRAINT c_filter_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: folder_level c_folder_level_pk_folder; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_level
    ADD CONSTRAINT c_folder_level_pk_folder FOREIGN KEY (pk_folder) REFERENCES public.folder(pk_folder);


--
-- Name: folder c_folder_pk_dept; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT c_folder_pk_dept FOREIGN KEY (pk_dept) REFERENCES public.dept(pk_dept);


--
-- Name: folder c_folder_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT c_folder_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: folder_resource c_folder_resource_pk_folder; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_resource
    ADD CONSTRAINT c_folder_resource_pk_folder FOREIGN KEY (pk_folder) REFERENCES public.folder(pk_folder);


--
-- Name: frame_history c_frame_history_pk_alloc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame_history
    ADD CONSTRAINT c_frame_history_pk_alloc FOREIGN KEY (pk_alloc) REFERENCES public.alloc(pk_alloc);


--
-- Name: frame_history c_frame_history_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame_history
    ADD CONSTRAINT c_frame_history_pk_job FOREIGN KEY (pk_job) REFERENCES public.job_history(pk_job) ON DELETE CASCADE;


--
-- Name: frame_history c_frame_history_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame_history
    ADD CONSTRAINT c_frame_history_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer_history(pk_layer) ON DELETE CASCADE;


--
-- Name: frame c_frame_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame
    ADD CONSTRAINT c_frame_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: frame c_frame_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.frame
    ADD CONSTRAINT c_frame_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: host_local c_host_local_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_local
    ADD CONSTRAINT c_host_local_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: host_local c_host_local_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_local
    ADD CONSTRAINT c_host_local_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: host c_host_pk_alloc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host
    ADD CONSTRAINT c_host_pk_alloc FOREIGN KEY (pk_alloc) REFERENCES public.alloc(pk_alloc);


--
-- Name: host_stat c_host_stat_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.host_stat
    ADD CONSTRAINT c_host_stat_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: job_env c_job_env_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_env
    ADD CONSTRAINT c_job_env_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job_history c_job_history_pk_dept; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_history
    ADD CONSTRAINT c_job_history_pk_dept FOREIGN KEY (pk_dept) REFERENCES public.dept(pk_dept);


--
-- Name: job_history c_job_history_pk_facility; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_history
    ADD CONSTRAINT c_job_history_pk_facility FOREIGN KEY (pk_facility) REFERENCES public.facility(pk_facility);


--
-- Name: job_history c_job_history_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_history
    ADD CONSTRAINT c_job_history_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: job_local c_job_local_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_local
    ADD CONSTRAINT c_job_local_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: job_local c_job_local_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_local
    ADD CONSTRAINT c_job_local_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job_mem c_job_mem_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_mem
    ADD CONSTRAINT c_job_mem_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job c_job_pk_dept; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_pk_dept FOREIGN KEY (pk_dept) REFERENCES public.dept(pk_dept);


--
-- Name: job c_job_pk_facility; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_pk_facility FOREIGN KEY (pk_facility) REFERENCES public.facility(pk_facility);


--
-- Name: job c_job_pk_folder; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_pk_folder FOREIGN KEY (pk_folder) REFERENCES public.folder(pk_folder);


--
-- Name: job c_job_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT c_job_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: job_post c_job_post_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_post
    ADD CONSTRAINT c_job_post_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job_post c_job_post_pk_post_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_post
    ADD CONSTRAINT c_job_post_pk_post_job FOREIGN KEY (pk_post_job) REFERENCES public.job(pk_job);


--
-- Name: job_resource c_job_resource_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_resource
    ADD CONSTRAINT c_job_resource_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job_stat c_job_stat_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_stat
    ADD CONSTRAINT c_job_stat_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: job_usage c_job_usage_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_usage
    ADD CONSTRAINT c_job_usage_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_env c_layer_env_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_env
    ADD CONSTRAINT c_layer_env_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_env c_layer_env_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_env
    ADD CONSTRAINT c_layer_env_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: layer_history c_layer_history_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_history
    ADD CONSTRAINT c_layer_history_pk_job FOREIGN KEY (pk_job) REFERENCES public.job_history(pk_job) ON DELETE CASCADE;


--
-- Name: layer_mem c_layer_mem_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_mem
    ADD CONSTRAINT c_layer_mem_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_mem c_layer_mem_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_mem
    ADD CONSTRAINT c_layer_mem_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: layer_output c_layer_output_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_output
    ADD CONSTRAINT c_layer_output_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_output c_layer_output_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_output
    ADD CONSTRAINT c_layer_output_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: layer c_layer_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT c_layer_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_resource c_layer_resource_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_resource
    ADD CONSTRAINT c_layer_resource_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_resource c_layer_resource_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_resource
    ADD CONSTRAINT c_layer_resource_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: layer_stat c_layer_stat_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_stat
    ADD CONSTRAINT c_layer_stat_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_stat c_layer_stat_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_stat
    ADD CONSTRAINT c_layer_stat_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: layer_usage c_layer_usage_pk_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_usage
    ADD CONSTRAINT c_layer_usage_pk_job FOREIGN KEY (pk_job) REFERENCES public.job(pk_job);


--
-- Name: layer_usage c_layer_usage_pk_layer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_usage
    ADD CONSTRAINT c_layer_usage_pk_layer FOREIGN KEY (pk_layer) REFERENCES public.layer(pk_layer);


--
-- Name: matcher c_matcher_pk_filter; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matcher
    ADD CONSTRAINT c_matcher_pk_filter FOREIGN KEY (pk_filter) REFERENCES public.filter(pk_filter);


--
-- Name: owner c_owner_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.owner
    ADD CONSTRAINT c_owner_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: point c_point_pk_dept; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.point
    ADD CONSTRAINT c_point_pk_dept FOREIGN KEY (pk_dept) REFERENCES public.dept(pk_dept);


--
-- Name: point c_point_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.point
    ADD CONSTRAINT c_point_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: proc c_proc_pk_frame; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc
    ADD CONSTRAINT c_proc_pk_frame FOREIGN KEY (pk_frame) REFERENCES public.frame(pk_frame);


--
-- Name: proc c_proc_pk_host; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc
    ADD CONSTRAINT c_proc_pk_host FOREIGN KEY (pk_host) REFERENCES public.host(pk_host);


--
-- Name: show_alias c_show_alias_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.show_alias
    ADD CONSTRAINT c_show_alias_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: show_service c_show_service_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.show_service
    ADD CONSTRAINT c_show_service_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: subscription c_subscription_pk_alloc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT c_subscription_pk_alloc FOREIGN KEY (pk_alloc) REFERENCES public.alloc(pk_alloc);


--
-- Name: subscription c_subscription_pk_show; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT c_subscription_pk_show FOREIGN KEY (pk_show) REFERENCES public.show(pk_show);


--
-- Name: task c_task_pk_point; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT c_task_pk_point FOREIGN KEY (pk_point) REFERENCES public.point(pk_point);


--
-- PostgreSQL database dump complete
--

