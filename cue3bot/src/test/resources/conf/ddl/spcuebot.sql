--- SpCueBot SQL Schema
--- use the supplied init.sh to create a new DB.
 
CREATE SCHEMA spcue AUTHORIZATION cue;

---
--- A table of key value pairs for storing global
--- configuration options.
---
CREATE TABLE spcue.config (
    pk_config           VARCHAR(36) NOT NULL,
    s_key               VARCHAR(36) NOT NULL,
    i_value             INTEGER DEFAULT 0,
    l_value             BIGINT DEFAULT 0,
    s_value             TEXT DEFAULT '',
    b_value             BOOLEAN DEFAULT 'f'
);
ALTER TABLE ONLY spcue.config
    ADD CONSTRAINT config_pk PRIMARY KEY (pk_config);
ALTER TABLE spcue.config ADD CONSTRAINT config_s_key_uniq_idx UNIQUE (s_key); 


---
--- shows
---
CREATE TABLE spcue.shows (
    pk_show             VARCHAR(36) NOT NULL,   
    s_name              VARCHAR(36) NOT NULL,
    i_default_max_procs INTEGER DEFAULT 100 NOT NULL,
    i_default_min_procs INTEGER DEFAULT 1 NOT NULL,
    b_paused            BOOLEAN DEFAULT 'f' NOT NULL
);
---
ALTER TABLE ONLY spcue.shows
    ADD CONSTRAINT shows_pk PRIMARY KEY (pk_show);
ALTER TABLE spcue.shows ADD CONSTRAINT shows_s_name_uniq_idx UNIQUE (s_name);    


---
--- Groups are for organizing jobs
---
CREATE TABLE spcue.groups (
    pk_group                VARCHAR(36) NOT NULL,
    pk_parent_group         VARCHAR(36),
    pk_show                 VARCHAR(36) NOT NULL REFERENCES spcue.shows,
    s_name                  VARCHAR(36) NOT NULL,
    i_priority              INTEGER DEFAULT 1 NOT NULL,
    i_level                 INTEGER DEFAULT 0 NOT NULL,
    i_min_procs             INTEGER DEFAULT 0 NOT NULL,
    i_max_procs             INTEGER DEFAULT -1 NOT NULL,
    b_default               BOOLEAN DEFAULT 'f' NOT NULL
);
---
ALTER TABLE ONLY spcue.groups
    ADD CONSTRAINT groups_pk PRIMARY KEY (pk_group);

ALTER TABLE ONLY spcue.groups
    ADD CONSTRAINT groups_parent_name_uniq_idx UNIQUE (pk_parent_group,s_name);
    
ALTER TABLE ONLY spcue.groups
    ADD FOREIGN KEY (pk_parent_group) REFERENCES spcue.groups;

CREATE INDEX groups_s_name_idx ON spcue.groups USING BTREE (s_name);
CREATE INDEX groups_pk_show_idx ON spcue.groups USING BTREE (pk_show);

---
--- This trigger handles updating the i_level field in the groups table.
--- i_level is how deep the group is in the tree.
---
CREATE OR REPLACE FUNCTION spcue.trigger_group_parent_change() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.pk_parent_group IS NULL THEN
        RAISE EXCEPTION 'Unable to re-parent the root groups';
    END IF;

    IF OLD.pk_parent_group = NEW.pk_parent_group THEN
        RETURN NEW;
    END IF;
    PERFORM spcue.recurse_group_parent_change(NEW.pk_group, NEW.pk_parent_group);
    RETURN NEW;
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_group_parent_change AFTER UPDATE ON spcue.groups
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_group_parent_change();

---
--- This method is run when a group is reparented.  It will recursive update
--- the i_level field for a group and all of its sub groups.
---
CREATE OR REPLACE FUNCTION spcue.recurse_group_parent_change(VARCHAR, VARCHAR) RETURNS VOID AS $$
DECLARE
    s_group_id ALIAS FOR $1;
    s_parent_id ALIAS FOR $2;
    i_parent_level INTEGER;
    v_children RECORD;
BEGIN
    --- got the level of the new parent + 1.
    SELECT INTO i_parent_level i_level+1 FROM spcue.groups WHERE pk_group = s_parent_id;
    UPDATE spcue.groups SET i_level = i_parent_level WHERE pk_group= s_group_id;
    
    FOR v_children IN SELECT pk_group FROM spcue.groups WHERE pk_parent_group = s_group_id LOOP
        PERFORM spcue.recurse_group_parent_change(v_children.pk_group, s_group_id);
    END LOOP; 
END
$$
LANGUAGE plpgsql;

---
--- Filters are used for filtering jobs into groups
---
CREATE TABLE spcue.filters (
    pk_filter               VARCHAR(36) NOT NULL,
    pk_show                 VARCHAR(36) NOT NULL REFERENCES spcue.shows,
    s_name                  VARCHAR(128) NOT NULL,
    s_type                  VARCHAR(16) NOT NULL, --- ANY OR ALL
    f_order                 NUMERIC(6,2) DEFAULT 0.0 NOT NULL,
    b_enabled               BOOLEAN DEFAULT 't' NOT NULL    
);
---
ALTER TABLE ONLY spcue.filters
    ADD CONSTRAINT filter_pk PRIMARY KEY (pk_filter);
CREATE INDEX filters_pk_show_idx ON spcue.filters USING BTREE (pk_show); 

CREATE OR REPLACE FUNCTION spcue.reorder_filters(VARCHAR) RETURNS VOID AS $$
DECLARE
    i_new_order NUMERIC(6,2);
    r_filter RECORD;
    s_show ALIAS FOR $1;    
BEGIN
    i_new_order = 1;
    FOR r_filter IN SELECT pk_filter FROM spcue.filters WHERE pk_show=s_show ORDER BY f_order ASC LOOP
        UPDATE spcue.filters SET f_order=i_new_order WHERE pk_filter=r_filter.pk_filter;
        i_new_order := i_new_order + 1;
    END LOOP;
END
$$
LANGUAGE plpgsql;


---
--- Matchers are used to match something before executing an action
---
CREATE TABLE spcue.matchers (
    pk_matcher              VARCHAR(36) NOT NULL,
    pk_filter               VARCHAR(36) NOT NULL REFERENCES spcue.filters,
    s_subject               VARCHAR(64) NOT NULL,
    s_match                 VARCHAR(64) NOT NULL,
    s_value                 TEXT NOT NULL,
    t_creation_time         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
---
ALTER TABLE ONLY spcue.matchers
    ADD CONSTRAINT matcher_pk PRIMARY KEY (pk_matcher);
CREATE INDEX matchers_pk_filter_idx ON spcue.matchers USING BTREE (pk_filter); 


---
--- Actions are executed when its determined all matchers are positive.
---
CREATE TABLE spcue.actions (
    pk_action               VARCHAR(36) NOT NULL,
    pk_filter               VARCHAR(36) NOT NULL REFERENCES spcue.filters,
    pk_group                VARCHAR(36) REFERENCES spcue.groups,
    s_action                VARCHAR(24) NOT NULL,
    s_value_type            VARCHAR(24) NOT NULL,
    s_value                 TEXT,
    i_value                 INTEGER,
    b_value                 BOOLEAN,
    t_creation_time         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
); 
---
ALTER TABLE ONLY spcue.actions
    ADD CONSTRAINT action_pk PRIMARY KEY (pk_action);
CREATE INDEX actions_pk_filter_idx ON spcue.actions USING BTREE (pk_filter);  
CREATE INDEX actions_pk_group_idx ON spcue.actions USING BTREE (pk_group);

---
--- Jobs
---
CREATE TABLE spcue.jobs (
--- 
    pk_job                  VARCHAR(36) NOT NULL,
    pk_group                VARCHAR(36) REFERENCES spcue.groups,
    pk_show                 VARCHAR(36) NOT NULL,
    s_name                  VARCHAR(255) NOT NULL,
    s_base_name             VARCHAR(255) NOT NULL,
    s_verion                VARCHAR(255) NOT NULL,
    s_visible_name          VARCHAR(255),
    s_shot                  VARCHAR(32)  NOT NULL,
    s_user                  VARCHAR(32)  NOT NULL,
    s_state                 VARCHAR(16)  NOT NULL,
    s_log_dir               TEXT NOT NULL DEFAULT '',
    i_uid                   INTEGER DEFAULT 0 NOT NULL,
    i_priority              INTEGER DEFAULT 1 NOT NULL,
    i_min_procs             INTEGER DEFAULT 0 NOT NULL,
    i_max_procs             INTEGER DEFAULT 200 NOT NULL,
    i_start_time            INTEGER DEFAULT 0 NOT NULL,
    i_stop_time             INTEGER DEFAULT 0 NOT NULL,
    i_update_time           INTEGER DEFAULT 0 NOT NULL,
    b_paused                BOOLEAN DEFAULT 'f' NOT NULL,  
    b_autoeat               BOOLEAN DEFAULT 'f' NOT NULL
);
---
ALTER TABLE ONLY spcue.jobs
    ADD CONSTRAINT jobs_pk PRIMARY KEY (pk_job);
ALTER TABLE ONLY spcue.jobs
    ADD CONSTRAINT s_visible_name_uniq UNIQUE (s_visible_name);
    
CREATE INDEX jobs_pk_group_idx ON spcue.jobs USING BTREE (pk_group);
CREATE INDEX jobs_pk_show_idx ON spcue.jobs USING BTREE (pk_show);
CREATE INDEX jobs_s_name_idx ON spcue.jobs USING BTREE (s_name);
CREATE INDEX jobs_i_update_time_idx ON spcue.jobs USING BTREE (i_update_time);
CREATE INDEX jobs_s_state_idx ON spcue.jobs USING BTREE (s_state);
---
---

---
--- Layers
---
CREATE TABLE spcue.layers (
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    pk_show                 VARCHAR(36) NOT NULL,
    s_name                  VARCHAR(256) NOT NULL,
    s_cmd                   TEXT NOT NULL,
    s_range                 TEXT NOT NULL,
    i_chunk_size            INTEGER DEFAULT 1 NOT NULL,
    i_dispatch_order        INTEGER DEFAULT 1 NOT NULL,
    i_cores_min             INTEGER DEFAULT 100 NOT NULL,
    i_mem_min               BIGINT DEFAULT 4194304 NOT NULL,
    s_tags                  TEXT DEFAULT '' NOT NULL,
    s_type                  VARCHAR(16) NOT NULL
);
---
ALTER TABLE ONLY spcue.layers
    ADD CONSTRAINT layers_pk PRIMARY KEY (pk_layer);
CREATE INDEX layers_pk_job_idx ON spcue.layers USING BTREE (pk_job);
CREATE INDEX layers_pk_show_idx ON spcue.layers USING BTREE (pk_show);
CREATE INDEX layers_s_name_idx ON spcue.layers USING BTREE (s_name);
---
---


---
--- Hosts
---
CREATE TABLE spcue.hosts (
    pk_host                 VARCHAR(36) NOT NULL,
    pk_alloc                VARCHAR(36) NOT NULL,
    s_name                  VARCHAR(36) NOT NULL,
    s_state                 VARCHAR(36) NOT NULL,
    s_lock_state            VARCHAR(36) NOT NULL,
    b_nimby                 BOOLEAN DEFAULT 'f' NOT NULL,
    i_boot_time             INTEGER DEFAULT 0 NOT NULL,
    i_ping_time             INTEGER DEFAULT 0 NOT NULL,
    i_cores                 INTEGER DEFAULT 0 NOT NULL,
    i_procs                 INTEGER DEFAULT 0 NOT NULL,
    i_cores_idle            INTEGER DEFAULT 0 NOT NULL,
    i_mem                   BIGINT DEFAULT 0 NOT NULL,
    i_mem_idle              BIGINT DEFAULT 0 NOT NULL,
    s_alloc_tag             TEXT,
    s_tags                  TEXT,
    s_rqd_tags              TEXT,
    s_manual_tags           TEXT,
    fti_tags                TSVECTOR,
    b_unlock_boot           BOOLEAN NOT NULL DEFAULT 'f',
    b_unlock_idle           BOOLEAN NOT NULL DEFAULT 'f'
);

ALTER TABLE ONLY spcue.hosts
    ADD CONSTRAINT hosts_pk PRIMARY KEY (pk_host);   
ALTER TABLE ONLY spcue.hosts ADD CONSTRAINT s_name_uniq_idx UNIQUE (s_name);
CREATE INDEX hosts_pk_alloc_idx ON spcue.hosts USING BTREE (pk_alloc);
CREATE INDEX hosts_s_state_idx ON spcue.hosts USING BTREE (s_state);
CREATE INDEX hosts_s_lock_state_idx ON spcue.hosts USING BTREE (s_lock_state);
CREATE INDEX hosts_ft_tags_idx ON spcue.hosts USING GIST(fti_tags);

--- updates the FTI column when the host is updated
CREATE TRIGGER hosts_ts_vector_update BEFORE UPDATE OR INSERT ON spcue.hosts
    FOR EACH ROW EXECUTE PROCEDURE tsvector_update_trigger(fti_tags, 'pg_catalog.english', s_tags, s_alloc_tag, s_rqd_tags, s_manual_tags);

    
---
---  checks to make sure a host is not overallocated
---
CREATE OR REPLACE FUNCTION spcue.trigger_check_host_resources() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.i_cores_idle < 0 THEN
        RAISE EXCEPTION 'Unable to allocate additional core units, %', NEW.i_cores_idle;
    END IF;
    
    IF NEW.i_mem_idle < 0 THEN
        RAISE EXCEPTION 'Unable to allocate addtional memory, %', NEW.i_mem_idle;
    END IF;
    RETURN NEW;
END
$$
LANGUAGE plpgsql;  
---
---
CREATE TRIGGER trigger_update_host_resources BEFORE UPDATE ON spcue.hosts
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_check_host_resources();   
       

---
--- Host stats
---
CREATE TABLE spcue.host_stats (
---    
    pk_host_stat           VARCHAR(36) NOT NULL,
    pk_host                VARCHAR(36) NOT NULL,
    i_mem_total            INTEGER DEFAULT 0 NOT NULL,
    i_mem_free             INTEGER DEFAULT 0 NOT NULL,
    i_swap_total           INTEGER DEFAULT 0 NOT NULL,
    i_swap_free            INTEGER DEFAULT 0 NOT NULL,
    i_mcp_total            INTEGER DEFAULT 0 NOT NULL,
    i_mcp_free             INTEGER DEFAULT 0 NOT NULL,
    i_load                 INTEGER DEFAULT 0 NOT NULL,
    b_over_loaded           BOOLEAN DEFAULT 'f' NOT NULL
);
---
ALTER TABLE ONLY spcue.host_stats
    ADD CONSTRAINT host_stats_pk PRIMARY KEY (pk_host);
CREATE INDEX host_stats_pk_host_idx ON spcue.host_stats USING BTREE (pk_host);
---

--- 
--- Procs
---
CREATE TABLE spcue.procs (
    pk_proc                 VARCHAR(36) NOT NULL,
    pk_host                 VARCHAR(36) NOT NULL REFERENCES spcue.hosts,
    pk_job                  VARCHAR(36),
    pk_show                 VARCHAR(36),  
    pk_layer                VARCHAR(36),
    pk_frame                VARCHAR(36),
    i_cores_reserved        INTEGER NOT NULL,
    i_mem_reserved          INTEGER NOT NULL,
    i_mem_used              BIGINT DEFAULT 0 NOT NULL,
    i_mem_max_used          BIGINT DEFAULT 0 NOT NULL,
    i_last_update           INTEGER DEFAULT 0 NOT NULL,
    i_booked_time           INTEGER DEFAULT 0 NOT NULL,
    b_unbooked              BOOLEAN NOT NULL DEFAULT 'f'
);
---
ALTER TABLE ONLY spcue.procs
    ADD CONSTRAINT procs_pk PRIMARY KEY (pk_proc);
    
ALTER TABLE ONLY spcue.procs
    ADD CONSTRAINT procs_pk_frame_unique_idx UNIQUE (pk_frame);
CREATE INDEX procs_pk_host_idx ON spcue.procs USING BTREE (pk_host);
CREATE INDEX procs_pk_job_idx ON spcue.procs USING BTREE (pk_job);
CREATE INDEX procs_pk_layer_idx ON spcue.procs USING BTREE (pk_layer);
CREATE INDEX procs_pk_show_idx ON spcue.procs USING BTREE (pk_show);
---
---
---

---
--- Updates the host and subscription when a proc is created
---
CREATE OR REPLACE FUNCTION spcue.trigger_insert_proc_update_host() RETURNS TRIGGER AS $$
BEGIN
    UPDATE spcue.hosts SET 
        i_cores_idle = i_cores_idle - NEW.i_cores_reserved,
        i_mem_idle = i_mem_idle - NEW.i_mem_reserved
    WHERE
        pk_host=NEW.pk_host;

    RETURN NEW;    
END
$$
LANGUAGE plpgsql;
---
CREATE TRIGGER trigger_insert_proc_update_host AFTER INSERT ON spcue.procs
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_insert_proc_update_host();        
---


---
--- Updates the job/layer resources counts when a proc is created
--- TODO: eliminate the job_resources table. 
---
CREATE OR REPLACE FUNCTION spcue.trigger_insert_proc_update_resource_counts() RETURNS TRIGGER AS $$
BEGIN    
    UPDATE spcue.layer_resources SET 
        i_procs=i_procs + 1, 
        i_cores=i_cores + NEW.i_cores_reserved,
        i_mem_reserved = i_mem_reserved + NEW.i_mem_reserved
    WHERE
        pk_layer = NEW.pk_layer;

    RETURN NEW;    
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_insert_proc_update_resource_counts AFTER INSERT ON spcue.procs
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_insert_proc_update_resource_counts();
---
---


---
--- Updates the host and subscription when a proc is removed
---
CREATE OR REPLACE FUNCTION spcue.trigger_delete_proc_update_host() RETURNS TRIGGER AS $$
BEGIN
    UPDATE spcue.hosts SET 
        i_cores_idle = i_cores_idle + OLD.i_cores_reserved,
        i_mem_idle = i_mem_idle + OLD.i_mem_reserved
    WHERE
        pk_host=OLD.pk_host;
    RETURN OLD;    
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_delete_proc_update_host AFTER DELETE ON spcue.procs
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_delete_proc_update_host();
---


---
--- Updates the job/layer resource counts when a proc is removed.
---
CREATE OR REPLACE FUNCTION spcue.trigger_delete_proc_update_resource_counts() RETURNS TRIGGER AS $$
BEGIN
    UPDATE spcue.layer_resources SET 
        i_procs=i_procs - 1, 
        i_cores=i_cores - OLD.i_cores_reserved,
        i_mem_reserved = i_mem_reserved - OLD.i_mem_reserved
    WHERE
        pk_layer = OLD.pk_layer;
    RETURN OLD;    
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_delete_proc_update_resource_counts AFTER DELETE ON spcue.procs
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_delete_proc_update_resource_counts();
---



---
--- Handles moving the resource counts from 1 layer to another when a proc switches layers.
---
CREATE OR REPLACE FUNCTION spcue.trigger_update_proc_layer_resources() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.pk_layer != OLD.pk_layer THEN
            
        UPDATE spcue.layer_resources SET 
            i_procs=i_procs - 1, 
            i_cores=i_cores - OLD.i_cores_reserved,
            i_mem_reserved = i_mem_reserved - OLD.i_mem_reserved
        WHERE
            pk_layer = OLD.pk_layer;        
        
        UPDATE spcue.layer_resources SET 
            i_procs=i_procs + 1, 
            i_cores=i_cores + NEW.i_cores_reserved,
            i_mem_reserved = i_mem_reserved + NEW.i_mem_reserved
        WHERE
            pk_layer = NEW.pk_layer;
    END IF;
   RETURN NEW;
END
$$
LANGUAGE plpgsql;   
---
CREATE TRIGGER trigger_update_proc_layer_resources AFTER UPDATE ON spcue.procs
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_update_proc_layer_resources();
---
---


---
--- Frames
---
CREATE TABLE spcue.frames (
---
    pk_frame                VARCHAR(36) NOT NULL,
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    pk_show                 VARCHAR(36) NOT NULL,
    s_name                  VARCHAR(256) NOT NULL,
    s_state                 VARCHAR(24) NOT NULL,
    i_number                INTEGER NOT NULL,
    i_depend_count          INTEGER DEFAULT 0 NOT NULL,
    i_exit_status           INTEGER DEFAULT -1 NOT NULL,              
    i_retries               INTEGER DEFAULT 0 NOT NULL,
    i_mem_reserved          BIGINT DEFAULT 0 NOT NULL,
    i_mem_max_used          BIGINT DEFAULT 0 NOT NULL,
    i_mem_used              BIGINT DEFAULT 0 NOT NULL,
    i_dispatch_order        INTEGER DEFAULT 0 NOT NULL,
    i_start_time            INTEGER DEFAULT 0 NOT NULL,
    i_stop_time             INTEGER DEFAULT 0 NOT NULL,
    i_last_runtime          INTEGER DEFAULT 0 NOT NULL,
    i_last_update           INTEGER DEFAULT 0 NOT NULL, 
    s_last_resource         VARCHAR(64)
    
);

ALTER TABLE ONLY spcue.frames
    ADD CONSTRAINT frames_pk PRIMARY KEY (pk_frame);
    
CREATE INDEX frames_pk_job_frame_idx ON spcue.frames USING btree (pk_job);
CREATE INDEX frames_pk_job_layer_idx ON spcue.frames USING btree (pk_layer);
CREATE INDEX frames_s_name_idx ON spcue.frames USING btree (s_name);
CREATE INDEX frames_i_last_update_idx ON spcue.frames USING btree (i_last_update);
CREATE INDEX frames_i_dispatch_order_idx ON spcue.frames USING btree (i_dispatch_order);
CREATE INDEX frames_pk_job_frame_state_idx ON spcue.frames USING btree (pk_job,s_state);
---


---
--- When the status of a frame changes then then the layer_stats table is updated
--- with the new counts.
---
CREATE OR REPLACE FUNCTION spcue.trigger_frame_status_change() RETURNS TRIGGER AS $$
DECLARE
    s_old_status_col VARCHAR;
    s_new_status_col VARCHAR;
BEGIN
    IF OLD.s_state = 'Setup' THEN
        RETURN NEW;
    END IF;

    IF OLD.s_state!= NEW.s_state THEN 
        s_old_status_col := 'i_' || lower(OLD.s_state) || '_count';
        s_new_status_col := 'i_' || lower(NEW.s_state) || '_count';

        EXECUTE 'UPDATE spcue.layer_stats SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
            || s_new_status_col || '=' || s_new_status_col || '+1 WHERE pk_layer=' || quote_literal(NEW.pk_layer);

    END IF;
    RETURN NEW;
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_frame_status_change AFTER UPDATE ON spcue.frames
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_frame_status_change();
---


---
--- When a frame succeeds, add the time I took to run to the resource table.
---    
CREATE OR REPLACE FUNCTION spcue.trigger_frame_resource_count() RETURNS TRIGGER AS $$
BEGIN
    --- 
    --- When the frame is stopped this will update proc seconds or proc seconds lost
    --- depending on the state of the frame. 
    --- 
    IF OLD.s_state = 'Setup' THEN
        RETURN NEW;
    END IF;

    IF OLD.i_stop_time = 0 
        AND NEW.i_stop_time > 0 THEN
        
        IF NEW.s_state = 'Succeeded' THEN

            UPDATE spcue.layer_usage SET 
                i_proc_seconds = i_proc_seconds + (NEW.i_stop_time - NEW.i_start_time)
            WHERE pk_layer = NEW.pk_layer;

        ELSE 
            UPDATE spcue.layer_usage SET 
                i_proc_seconds_lost = i_proc_seconds_lost + (NEW.i_stop_time - NEW.i_start_time)
            WHERE pk_layer = NEW.pk_layer;

        END IF;
    END IF;
    RETURN NEW;
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_frame_resource_count AFTER UPDATE ON spcue.frames
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_frame_resource_count();
---
---
  

--- 
--- Dependencies
---
CREATE TABLE spcue.depends (
--- dependencies, does not reference other tables
    pk_depend               VARCHAR(36) NOT NULL,
    pk_parent               VARCHAR(36),
    pk_job_depend_on        VARCHAR(36) NOT NULL,
    pk_job_depend_er        VARCHAR(36) NOT NULL,
    pk_frame_depend_on      VARCHAR(36),
    pk_frame_depend_er      VARCHAR(36),
    pk_layer_depend_on      VARCHAR(36),
    pk_layer_depend_er      VARCHAR(36),
    i_chunk_size            INTEGER NOT NULL DEFAULT 1,
    s_type                  VARCHAR(36) NOT NULL,
    b_active                BOOLEAN DEFAULT 't' NOT NULL,
    b_any                   BOOLEAN DEFAULT 'f' NOT NULL
);

ALTER TABLE ONLY spcue.depends
    ADD CONSTRAINT depends_pk PRIMARY KEY (pk_depend);

CREATE INDEX depends_pk_parent_idx ON spcue.depends USING btree (pk_parent);    
CREATE INDEX depends_pk_job_depend_on_idx ON spcue.depends USING btree (pk_job_depend_on);
CREATE INDEX depends_pk_job_depend_er_idx ON spcue.depends USING btree (pk_job_depend_er);
CREATE INDEX depends_pk_frame_depend_on_idx ON spcue.depends USING btree (pk_frame_depend_on);
CREATE INDEX depends_pk_layer_depend_on_idx ON spcue.depends USING btree (pk_layer_depend_on);

---
--- Handles decrementing the individual frame dependency counts for frame-by-frame depends.
---
CREATE OR REPLACE FUNCTION spcue.trigger_frame_depend_satisfied() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.pk_parent IS NOT NULL AND OLD.b_active = 't' AND NEW.b_active = 'f' THEN
        EXECUTE 'UPDATE spcue.frames SET i_depend_count = i_depend_count - 1 WHERE 
            pk_job=' || quote_literal(NEW.pk_job_depend_er) || ' AND pk_frame=' || quote_literal(NEW.pk_frame_depend_er);
    END IF;
    RETURN NEW;
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER trigger_frame_depend_satisfied AFTER UPDATE ON spcue.depends
    FOR EACH ROW EXECUTE PROCEDURE spcue.trigger_frame_depend_satisfied();
---
    

---
--- Allocations
---
CREATE TABLE spcue.allocs (
---
    pk_alloc                 VARCHAR(36) NOT NULL,
    s_name                   VARCHAR(36) NOT NULL,
    s_tag                    VARCHAR(36) NOT NULL,
    s_orientation_type       VARCHAR(12) NOT NULL,
    b_allow_edit             BOOLEAN DEFAULT 't' NOT NULL
);
---
ALTER TABLE ONLY spcue.allocs
    ADD CONSTRAINT alloc_pk PRIMARY KEY (pk_alloc); 
---

---
--- Subscriptions
---
CREATE table spcue.subscriptions (
    pk_subscription         VARCHAR(36) NOT NULL,
    pk_alloc                VARCHAR(36) NOT NULL REFERENCES spcue.allocs (pk_alloc),
    pk_show                 VARCHAR(36) NOT NULL REFERENCES spcue.shows (pk_show),
    s_name                  VARCHAR(32) NOT NULL,
    i_size                  INTEGER NOT NULL DEFAULT 0,
    i_burst                 INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE ONLY spcue.subscriptions
    ADD CONSTRAINT subscriptions_pk PRIMARY KEY (pk_subscription);
---
ALTER TABLE ONLY spcue.subscriptions
    ADD CONSTRAINT subscriptions_pk_alloc_pk_show_uniq_idx UNIQUE (pk_show, pk_alloc);
CREATE INDEX subscriptions_pk_alloc_idx ON spcue.subscriptions USING btree (pk_alloc);    
---


---
---
---
---
CREATE TABLE spcue.layer_usage (
    pk_layer_usage          VARCHAR(36) NOT NULL,
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    i_proc_seconds          BIGINT DEFAULT 0 NOT NULL,
    i_proc_seconds_lost     BIGINT DEFAULT 0 NOT NULL
);
  
ALTER TABLE ONLY spcue.layer_usage
    ADD CONSTRAINT layer_usage_pk PRIMARY KEY (pk_layer_usage);
ALTER TABLE spcue.layer_usage ADD CONSTRAINT layer_usage_pk_layer_unique_idx UNIQUE (pk_layer);

---
--- Resources assigned to a layer
---
CREATE TABLE spcue.layer_resources (
    pk_layer_resource       VARCHAR(36) NOT NULL,
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    i_procs                 INTEGER DEFAULT 0 NOT NULL,
    i_cores                 INTEGER DEFAULT 0 NOT NULL,
    i_mem_reserved          BIGINT DEFAULT 0 NOT NULL
);
ALTER TABLE ONLY spcue.layer_resources
    ADD CONSTRAINT layer_resources_pk PRIMARY KEY (pk_layer_resource);
ALTER TABLE spcue.layer_resources ADD CONSTRAINT layer_resources_pk_layer_unique_idx UNIQUE (pk_layer);
CREATE INDEX layer_resources_pk_job_idx ON spcue.layer_resources USING BTREE (pk_job);

---
--- Keeps track of the total number of each frame in a particular state.
---
CREATE TABLE spcue.layer_stats (
---
    pk_layer_stats         VARCHAR(36) NOT NULL,
    pk_layer               VARCHAR(36) NOT NULL,
    pk_job                 VARCHAR(36) NOT NULL,       --- makes it easy to delete when the job is done
    i_total_count          INTEGER DEFAULT 0 NOT NULL,
    i_waiting_count        INTEGER DEFAULT 0 NOT NULL,
    i_running_count        INTEGER DEFAULT 0 NOT NULL,
    i_dead_count           INTEGER DEFAULT 0 NOT NULL,
    i_depend_count         INTEGER DEFAULT 0 NOT NULL,
    i_eaten_count          INTEGER DEFAULT 0 NOT NULL,
    i_succeeded_count      INTEGER DEFAULT 0 NOT NULL,
    i_reserved_count       INTEGER DEFAULT 0 NOT NULL,
    i_retry_count          INTEGER DEFAULT 0 NOT NULL,
    i_stopped_count        INTEGER DEFAULT 0 NOT NULL
);
    

ALTER TABLE ONLY spcue.layer_stats
    ADD CONSTRAINT layer_stats_pk PRIMARY KEY (pk_layer_stats);
CREATE INDEX layer_stats_pk_layer_idx ON spcue.layer_stats USING BTREE (pk_layer);
CREATE INDEX layer_stats_pk_job_idx ON spcue.layer_stats USING BTREE (pk_job);
CREATE INDEX layer_stats_i_waiting_count_idx ON spcue.layer_stats USING BTREE (i_waiting_count);


---
--- Some default shows/allocs to get started
---

INSERT INTO spcue.config (pk_config,s_key,i_value) VALUES ('00000000-0000-0000-0000-000000000000','MAX_PING_TIME',300);
INSERT INTO spcue.config (pk_config,s_key,i_value) VALUES ('00000000-0000-0000-0000-000000000001','MIN_CORES_REQUIRED', 10);
INSERT INTO spcue.config (pk_config,s_key,l_value) VALUES ('00000000-0000-0000-0000-000000000002','MIN_MEM_REQUIRED',500000);
INSERT INTO spcue.config (pk_config,s_key,l_value) VALUES ('00000000-0000-0000-0000-000000000003','MAX_PPS',25);

--- Create a pipe and edu show
INSERT INTO spcue.shows (pk_show,s_name) VALUES ('00000000-0000-0000-0000-000000000000','pipe');
INSERT INTO spcue.shows (pk_show,s_name) VALUES ('00000000-0000-0000-0000-000000000001','edu');

INSERT INTO spcue.groups (pk_group,pk_show,s_name,i_priority,pk_parent_group,b_default) VALUES ('A0000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000','pipe',100,NULL,'t');
    
INSERT INTO spcue.groups (pk_group,pk_show,s_name,i_priority,pk_parent_group,b_default) VALUES ('B0000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000001','edu',100,NULL,'t');

-- create a general and desktop allocation
INSERT INTO spcue.allocs (pk_alloc, s_name, s_tag, b_allow_edit, s_orientation_type) VALUES ('00000000-0000-0000-0000-000000000000','General','general','f','ByProc');
INSERT INTO spcue.allocs (pk_alloc, s_name, s_tag, b_allow_edit, s_orientation_type) VALUES ('00000000-0000-0000-0000-000000000001','Desktop','desktop','f','ByProc'); 

--- give pipe and edu some allocated procs
INSERT INTO spcue.subscriptions (pk_subscription,pk_alloc, pk_show, i_size, i_burst, s_name) VALUES ('00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',10,15, 'pipe.General');
INSERT INTO spcue.subscriptions (pk_subscription,pk_alloc, pk_show, i_size, i_burst, s_name) VALUES ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000001',10,15, 'edu.General');

---
--- Views
---

---
--- Will show you new procs booked per minute assuming they don't finish
--- in a minute.  Just using this for troubleshooting right now.
--- 
CREATE VIEW vs_speed AS 
    SELECT 
        COUNT(*)/10.0 AS i_pps 
    FROM 
        spcue.procs 
    WHERE 
        extract(epoch FROM now()) - i_booked_time <= 10;

---
--- Lists procs that were not able to be killed
---
CREATE VIEW vs_orphan AS 
    SELECT 
        jobs.s_name AS job_name,
        frames.s_name AS frame_name, 
        EXTRACT(epoch FROM now()) - procs.i_last_update AS last_update, 
        procs.i_cores_reserved 
    FROM 
        spcue.procs,
        spcue.frames,
        spcue.jobs 
    WHERE 
        jobs.pk_job = procs.pk_job
    AND
        procs.pk_frame = frames.pk_frame 
    AND 
        (procs.pk_frame IS NULL OR extract(epoch FROM now()) - procs.i_last_update > 300);
        
---
--- Stats and resource tables.  Frame status counts are maintained by layer
--- but views exist for seeing them by 
---
   
---
--- Frame counts by show
---
CREATE VIEW vs_show_stats AS
    SELECT
        jobs.pk_show,
        SUM(i_waiting_count) AS i_waiting_count,
        SUM(i_running_count) AS i_running_count,
        SUM(i_dead_count) AS i_dead_count,
        SUM(i_depend_count) AS i_depend_count,
        SUM(i_eaten_count) AS i_eaten_count,
        SUM(i_succeeded_count) AS i_succeeded_count,
        SUM(i_reserved_count) AS i_reserved_count,
        SUM(i_total_count) AS i_total_count,
        SUM(i_retry_count) AS i_retry_count,
        SUM(i_stopped_count) AS i_stopped_count
    FROM
        spcue.layer_stats,
        spcue.jobs,
        spcue.shows
    WHERE
        layer_stats.pk_job = jobs.pk_job
    AND
        jobs.s_state = 'Pending'
    GROUP BY jobs.pk_show;

---
--- Frame counts by group
---
CREATE VIEW vs_group_stats AS
    SELECT
        jobs.pk_group,
        SUM(i_waiting_count) AS i_waiting_count,
        SUM(i_running_count) AS i_running_count,
        SUM(i_dead_count) AS i_dead_count,
        SUM(i_depend_count) AS i_depend_count,
        SUM(i_eaten_count) AS i_eaten_count,
        SUM(i_succeeded_count) AS i_succeeded_count,
        SUM(i_reserved_count) AS i_reserved_count,
        SUM(i_total_count) AS i_total_count,
        SUM(i_retry_count) AS i_retry_count,
        SUM(i_stopped_count) AS i_stopped_count
    FROM
        spcue.layer_stats,
        spcue.jobs
    WHERE
        layer_stats.pk_job = jobs.pk_job
    AND 
        jobs.s_state = 'Pending'
    GROUP BY jobs.pk_group;    

---
--- frame counts by job
---
CREATE VIEW spcue.job_stats AS
    SELECT
        jobs.pk_job,
        SUM(i_waiting_count) AS i_waiting_count,
        SUM(i_running_count) AS i_running_count,
        SUM(i_dead_count) AS i_dead_count,
        SUM(i_depend_count) AS i_depend_count,
        SUM(i_eaten_count) AS i_eaten_count,
        SUM(i_succeeded_count) AS i_succeeded_count,
        SUM(i_reserved_count) AS i_reserved_count,
        SUM(i_total_count) AS i_total_count,
        SUM(i_retry_count) AS i_retry_count,
        SUM(i_stopped_count) AS i_stopped_count
    FROM
        spcue.layer_stats,
        spcue.jobs
    WHERE
        layer_stats.pk_job = jobs.pk_job
    GROUP BY jobs.pk_job;    
    
---
--- resources allocate dby show
--- 
CREATE VIEW vs_show_resources AS
    SELECT
        jobs.pk_show,
        SUM(i_procs) AS i_procs,
        SUM(i_cores) AS i_cores,
        SUM(i_mem_reserved) AS i_mem_reserved
    FROM
        spcue.jobs,
        spcue.layer_resources 
    WHERE
        layer_resources.pk_job = jobs.pk_job
    AND
        jobs.s_state='Pending'
    GROUP BY 
        jobs.pk_show;    

---
--- resources allocated by group
---
CREATE VIEW vs_group_resources AS
    SELECT
        jobs.pk_group,
        SUM(i_procs) AS i_procs,
        SUM(i_cores) AS i_cores,
        SUM(i_mem_reserved) AS i_mem_reserved
    FROM
        spcue.jobs,
        spcue.layer_resources 
    WHERE
        layer_resources.pk_job = jobs.pk_job
    AND
        jobs.s_state='Pending'
    GROUP BY 
        jobs.pk_group;    

---
--- resources allocated by job
---
CREATE VIEW vs_job_resources AS
    SELECT
        layer_resources.pk_job,
        SUM(i_procs) AS i_procs,
        SUM(i_cores) AS i_cores,
        SUM(i_mem_reserved) AS i_mem_reserved
    FROM
        spcue.layer_resources,
        spcue.jobs
    WHERE
        layer_resources.pk_job = jobs.pk_job
    AND
        jobs.s_state='Pending'
    GROUP BY
        layer_resources.pk_job;
        
---
--- resources allocated by host
--- 
CREATE VIEW vs_host_resources AS 
    SELECT 
        s_name,
        i_cores,
        i_cores_idle,
        i_cores-i_cores_idle AS cores_used, 
        i_mem,i_mem_idle, 
        i_mem - i_mem_idle AS mem_used
    FROM 
        spcue.hosts;

---
--- statistics by host
---
CREATE VIEW vs_host_stats AS
    SELECT
        hosts.pk_host, 
        hosts.s_name, 
        i_mem_total, 
        i_mem_free,
        i_swap_total,
        i_swap_free,
        i_mcp_total,
        i_mcp_free 
    FROM 
        spcue.hosts,
        spcue.host_stats 
    WHERE 
        hosts.pk_host = host_stats.pk_host;   

---
--- job usage - how much proc time a job used
---
CREATE VIEW spcue.job_usage AS
    SELECT
        layer_usage.pk_job,
        SUM(i_proc_seconds) AS i_proc_seconds,
        SUM(i_proc_seconds_lost) AS i_proc_seconds_lost 
    FROM
        spcue.layer_usage
    GROUP BY
        layer_usage.pk_job;
        
---
--- group usage
---   
CREATE VIEW spcue.group_usage AS
    SELECT
        jobs.pk_group,
        SUM(i_proc_seconds) AS i_proc_seconds,
        SUM(i_proc_seconds_lost) AS i_proc_seconds_lost 
    FROM
        spcue.layer_usage,
        spcue.jobs
    WHERE
        layer_usage.pk_job = jobs.pk_job
    AND
        jobs.s_state='Pending'
    GROUP BY
        jobs.pk_group;
        

CREATE VIEW spcue.show_usage AS
    SELECT
        jobs.pk_show,
        SUM(i_proc_seconds) AS i_proc_seconds,
        SUM(i_proc_seconds_lost) AS i_proc_seconds_lost 
    FROM
        spcue.layer_usage,
        spcue.jobs
    WHERE
        layer_usage.pk_job = jobs.pk_job
    AND
        jobs.s_state='Pending'
    GROUP BY
        jobs.pk_show;
                
---
--- Allocated resources by layer.  Mainly for troubleshooting.
---
CREATE VIEW vs_layer_resources AS
    SELECT
        jobs.s_state AS job_state,  
        jobs.s_name AS job_name,
        layers.s_name AS layer_name,
        layer_resources.i_proc_seconds,
        layer_resources.i_proc_seconds_lost,
        CASE WHEN layer_stats.i_succeeded_count > 0 THEN
            (layer_resources.i_proc_seconds / layer_stats.i_succeeded_count)
        ELSE 0 END AS i_avg_seconds,
        layer_resources.i_procs,
        layer_resources.i_cores,
        layer_resources.i_mem_reserved,
        COALESCE((SELECT SUM(procs.i_mem_used) FROM spcue.procs WHERE layers.pk_layer = procs.pk_layer),0) AS i_mem_used,  
        COALESCE((SELECT SUM(procs.i_mem_max_used) FROM spcue.procs WHERE layers.pk_layer = procs.pk_layer),0) AS i_mem_max_used   
    FROM
        spcue.jobs,
        spcue.layers,
        spcue.layer_resources,
        spcue.layer_stats
   WHERE
        jobs.pk_job = layers.pk_job
   AND
        layers.pk_layer = layer_stats.pk_layer
   AND
        layers.pk_layer = layer_resources.pk_layer;



    
