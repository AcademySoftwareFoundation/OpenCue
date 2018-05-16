BEGIN;
 
---
--- A table of key value pairs for storing global
--- configuration options.
---
CREATE TABLE cue3.config (
    pk_config               VARCHAR2(36) NOT NULL,
    str_key                 VARCHAR2(36) NOT NULL,
    int_value               NUMBER(38) DEFAULT 0,
    long_value              NUMBER(38) DEFAULT 0,
    str_value               VARCHAR2(255) DEFAULT '',
    b_value                 NUMBER(1) DEFAULT 0
);
ALTER TABLE cue3.config
    ADD CONSTRAINT c_pk_pkconfig PRIMARY KEY (pk_config);
ALTER TABLE cue3.config ADD CONSTRAINT c_show_uk UNIQUE (str_key) using index tablespace users; 

---
--- shows
---
CREATE TABLE cue3.show (
    pk_show                 VARCHAR2(36) NOT NULL,   
    str_name                VARCHAR2(36) NOT NULL,
    int_default_max_procs   NUMBER(38) DEFAULT 100 NOT NULL,
    int_default_min_procs   NUMBER(38) DEFAULT 1 NOT NULL,
    b_paused                NUMBER(1) DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.show
    ADD CONSTRAINT c_show_pk PRIMARY KEY (pk_show);
ALTER TABLE cue3.show ADD CONSTRAINT show_s_name_uk UNIQUE (s_name);    
---


---
--- Folders are for organizing jobs
---
CREATE TABLE cue3.folder (
    pk_folder               VARCHAR2(36) NOT NULL,
    pk_parent_folder        VARCHAR2(36),
    pk_show                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(36) NOT NULL,
    int_priority            NUMBER(38) DEFAULT 1 NOT NULL,
    int_level               NUMBER(38) DEFAULT 0 NOT NULL,
    int_min_procs           NUMBER(38) DEFAULT 0 NOT NULL,
    int_max_procs           NUMBER(38) DEFAULT -1 NOT NULL,
    b_default               NUMBER(1) DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.folder
    ADD CONSTRAINT c_folder_pk PRIMARY KEY (pk_folder) USING INDEX TABLESPACE users;

ALTER TABLE cue3.folder
FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);

ALTER TABLE cue3.layer_stat ADD CONSTRAINT c_layer_stat_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);
    ADD CONSTRAINT c_folder_uk UNIQUE (pk_parent_folder, str_name) USING INDEX TABLESPACE users;

CREATE INDEX i_folder_strname ON cue3.folder  (str_name);
CREATE INDEX i_folder_pkshow ON cue3.folder  (pk_show);
CREATE INDEX i_folder_pkparentfolder on cue3.folder (pk_parent_folder);

ALTER TABLE cue3.folder ADD CONSTRAINT c_folder_pk_show 
FOREIGN KEY (pk_show) REFERENCES show (pk_show);
---

---
---
---
CREATE TABLE cue3.folder_level(
    pk_folder_level         VARCHAR2(36) NOT NULL,
    pk_folder               VARCHAR2(36) NOT NULL,
    int_level               NUMBER(38) DEFAULT 0 NOT NULL
);

ALTER TABLE cue3.folder_level
    ADD CONSTRAINT c_folder_level_pk PRIMARY KEY (pk_folder_level) USING INDEX TABLESPACE users;
    
ALTER TABLE cue3.folder_level
    ADD CONSTRAINT c_folder_level_uk UNIQUE (pk_folder) USING INDEX TABLESPACE users;

ALTER TABLE cue3.folder_level ADD CONSTRAINT c_folder_level_pk_folder FOREIGN KEY (pk_folder) REFERENCES folder (pk_folder);
---
--- Filters are used for filtering jobs into groups
---
CREATE TABLE cue3.filter (
    pk_filter               VARCHAR2(36) NOT NULL,
    pk_show                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(128) NOT NULL,
    str_type                VARCHAR2(16) NOT NULL,
    f_order                 NUMBER(6,2) DEFAULT 0.0 NOT NULL,
    b_enabled               NUMBER(1) DEFAULT 0 NOT NULL    
);
---
ALTER TABLE cue3.filter
    ADD CONSTRAINT c_filter_pk PRIMARY KEY (pk_filter);
CREATE INDEX i_filters_pk_show ON cue3.filter (pk_show);

ALTER TABLE cue3.filter ADD CONSTRAINT c_filter_pk_show 
FOREIGN KEY (pk_show) REFERENCES show (pk_show); 
---

---
--- Matchers are used to match something before executing an action
---
CREATE TABLE cue3.matcher (
    pk_matcher              VARCHAR2(36) NOT NULL,
    pk_filter               VARCHAR2(36) NOT NULL,
    str_subject             VARCHAR2(64) NOT NULL,
    str_match               VARCHAR2(64) NOT NULL,
    str_value               VARCHAR2(4000) NOT NULL,
    ts_created              TIMESTAMP DEFAULT systimestamp NOT NULL
);
---
ALTER TABLE  cue3.matcher
    ADD CONSTRAINT c_matcher_pk PRIMARY KEY (pk_matcher);
CREATE INDEX i_matcher_pk_filter ON cue3.matcher (pk_filter);

ALTER TABLE cue3.matcher ADD CONSTRAINT c_matcher_pk_filter 
FOREIGN KEY (pk_filter) REFERENCES filter (pk_filter);
---

---
--- Actions are executed when its determined all matchers are positive.
---
CREATE TABLE cue3.action (
    pk_action               VARCHAR2(36) NOT NULL,
    pk_filter               VARCHAR2(36) NOT NULL,
    pk_folder               VARCHAR2(36),
    str_action              VARCHAR2(24) NOT NULL,
    str_value_type          VARCHAR2(24) NOT NULL,
    str_value               VARCHAR2(4000),
    int_value               NUMBER(38),
    b_value                 NUMBER(1),
    ts_created              TIMESTAMP DEFAULT systimestamp NOT NULL
); 
---
ALTER TABLE  cue3.action
    ADD CONSTRAINT c_action_pk PRIMARY KEY (pk_action);
CREATE INDEX i_action_pk_filter ON cue3.action (pk_filter);  
CREATE INDEX i_action_pk_group ON cue3.action (pk_group);

ALTER TABLE cue3.action ADD CONSTRAINT c_action_pk_filter 
    FOREIGN KEY (pk_filter) REFERENCES filter (pk_filter);

ALTER TABLE cue3.action ADD CONSTRAINT c_action_pk_folder 
    FOREIGN KEY (pk_folder) REFERENCES folder (pk_folder);

---
--- Jobs
---
CREATE TABLE cue3.job (
    pk_job                  VARCHAR2(36) NOT NULL,
    pk_group                VARCHAR2(36) NOT NULL,
    pk_show                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(255) NOT NULL,
    str_base_name           VARCHAR2(255) NOT NULL,
    str_verion              VARCHAR2(255) NOT NULL,
    str_visible_name        VARCHAR2(255),
    str_shot                VARCHAR2(32) NOT NULL,
    str_user                VARCHAR2(32) NOT NULL,
    str_state               VARCHAR2(16) NOT NULL,
    str_log_dir             VARCHAR2(4000) DEFAULT '' NOT NULL,
    int_uid                 NUMBER(38) DEFAULT 0 NOT NULL,
    int_priority            NUMBER(38) DEFAULT 1 NOT NULL,
    int_min_procs           NUMBER(38) DEFAULT 0 NOT NULL,
    int_max_procs           NUMBER(38) DEFAULT 200 NOT NULL,
    ts_started              TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_updated              TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_stopped              TIMESTAMP,
    b_paused                NUMBER(1) DEFAULT 0 NOT NULL,  
    b_autoeat               NUMBER(1) DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.job
    ADD CONSTRAINT c_job_pk PRIMARY KEY (pk_job);

ALTER TABLE cue3.job
    ADD CONSTRAINT c_job_uk UNIQUE (str_visible_name);
    
CREATE INDEX i_job_pk_group ON cue3.job (pk_group);
CREATE INDEX i_job_pk_show ON cue3.job (pk_show);
CREATE INDEX i_job_str_name ON cue3.job (str_name);
CREATE INDEX i_job_str_state ON cue3.job (str_state); 
CREATE INDEX i_job_booking_state ON cue3.job (b_paused, b_auto_book);

ALTER TABLE cue3.job ADD CONSTRAINT c_job_pk_folder
FOREIGN KEY (pk_folder) REFERENCES folder (pk_folder);

ALTER TABLE cue3.job ADD CONSTRAINT c_job_pk_show
FOREIGN KEY (pk_show) REFERENCES show (pk_show);
---

CREATE TABLE cue3.job_tier (
    pk_job_tier             VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_tier                NUMBER(6),
    int_book                NUMBER(6)
);
ALTER TABLE cue3.job_tier
    ADD CONSTRAINT c_job_tier_pk PRIMARY KEY (pk_job_tier);

ALTER TABLE cue3.job_tier
    ADD CONSTRAINT c_job_tier_uk UNIQUE (pk_job);
---

---
--- job_env
--- 
CREATE TABLE cue3.job_env (
    pk_job_env              VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36),
    str_key                 VARCHAR2(36),
    str_value               VARCHAR2(2048)
);
 ---
ALTER TABLE cue3.job_env
    ADD CONSTRAINT c_job_env_pk PRIMARY KEY (pk_job_env);
    
CREATE INDEX i_job_env_pk_job ON cue3.job_env (pk_job);

ALTER TABLE cue3.job_env ADD CONSTRAINT c_job_env_pk_job
    FOREIGN KEY (pk_job) REFERENCES job (pk_job);
---

/**
*
* job_lock is used to coordinate dispatching.
* PLEASE NOTE: there is no forign key constraint from job_lock.pk_job
* to job.pk_job because it could introduce deadlock situations.
**/
CREATE TABLE cue3.job_lock (
    pk_job_lock             VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36),
    int_semaphore           NUMBER(8)
);

ALTER TABLE cue3.job_lock
    ADD CONSTRAINT c_job_lock_pk PRIMARY KEY (pk_job_lock);
CREATE INDEX i_job_lock_pk_job ON cue3.job_lock (pk_job);
---

---
--- job comments
---
CREATE TABLE cue3.commnets (
    pk_comment              VARCHAR2(36) NOT NULL,       
    pk_job                  VARCHAR2(36),
    pk_host                 VARCHAR2(36),
    ts_created              TIMESTAMP DEFAULT systimestamp NOT NULL,
    str_user                VARCHAR2(36) NOT NULL,
    str_subject             VARCHAR2(36) NOT NULL,
    str_message             VARCHAR2(4000) NOT NULL
);
---
ALTER TABLE cue3.comments
    ADD CONSTRAINT c_comment_pk PRIMARY KEY (pk_comment);

CREATE INDEX i_comment_pk_job ON cue3.comments  (pk_job);
CREATE INDEX i_comment_pk_host ON cue3.comments  (pk_host);

ALTER TABLE cue3.comments ADD CONSTRAINT c_comment_pk_job
    FOREIGN KEY (pk_job) REFERENCES job (pk_job);

ALTER TABLE cue3.comments ADD CONSTRAINT c_comment_pk_host
    FOREIGN KEY (pk_host) REFERENCES host (pk_host);
---

    
---
--- Layers
---
CREATE TABLE cue3.layer (
    pk_layer                VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(256) NOT NULL,
    str_cmd                 VARCHAR2(4000) NOT NULL,
    str_range               VARCHAR2(4000) NOT NULL,
    int_chunk_size          NUMBER(38) DEFAULT 1 NOT NULL,
    int_dispatch_order      NUMBER(38) DEFAULT 1 NOT NULL,
    int_cores_min           NUMBER(38) DEFAULT 100 NOT NULL,
    int_mem_min             NUMBER(38) DEFAULT 4194304 NOT NULL,
    str_tags                VARCHAR2(4000) DEFAULT '' NOT NULL,
    str_type                VARCHAR2(16) NOT NULL
);
---
ALTER TABLE cue3.layer
    ADD CONSTRAINT c_layer_pk PRIMARY KEY (pk_layer);

ALTER TABLE cue3.layer
    ADD CONSTRAINT c_layer_str_name_unq UNIQUE (str_name, pk_job);

CREATE INDEX i_layer_pkjob ON cue3.layer  (pk_job);
CREATE INDEX i_layer_pkshow ON cue3.layer  (pk_show);
CREATE INDEX i_layer_int_dispatch_order ON cue3.layer (int_dispatch_order);
CREATE INDEX i_layer_cores_min ON cue3.layer (int_cores_min);
CREATE INDEX i_layer_mem_min ON cue3.layer (int_mem_min);

ALTER TABLE cue3.layer ADD CONSTRAINT c_layer_pk_job
    FOREIGN KEY (pk_job) REFERENCES job (pk_job);
    

    
---

---
--- job_env
--- 
CREATE TABLE cue3.layer_env (
    pk_layer_env              VARCHAR2(36) NOT NULL,
    pk_layer                VARCHAR2(36),
    pk_job                  VARCHAR2(36), 
    str_key                 VARCHAR2(36),
    str_value               VARCHAR2(2048)
);
 ---
ALTER TABLE cue3.layer_env
    ADD CONSTRAINT c_layer_env_pk PRIMARY KEY (pk_layer_env);
    
CREATE INDEX i_layer_env_pk_job ON cue3.layer_env (pk_job);
CREATE INDEX i_layer_env_pk_layer ON cue3.layer_env (pk_layer);

ALTER TABLE cue3.layer_env ADD CONSTRAINT c_layer_env_pk_job
    FOREIGN KEY (pk_job) REFERENCES job (pk_job);

ALTER TABLE cue3.layer_env ADD CONSTRAINT c_layer_env_pk_layer
    FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);
        
---

---
--- Hosts
---
CREATE TABLE cue3.host (
    pk_host                 VARCHAR2(36) NOT NULL,
    pk_alloc                VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(36) NOT NULL,
    str_state               VARCHAR2(36) NOT NULL,
    str_lock_state          VARCHAR2(36) NOT NULL,
    b_nimby                 NUMBER(1) DEFAULT 0 NOT NULL,
    ts_booted               TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_ping                 TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_created              TIMESTAMP DEFAULT systimestamp NOT NULL,
    int_cores               NUMBER(38) DEFAULT 0 NOT NULL,
    int_procs               NUMBER(38) DEFAULT 0 NOT NULL,
    int_cores_idle          NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem                 NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_idle            NUMBER(38) DEFAULT 0 NOT NULL,
    b_unlock_boot           NUMBER(1) DEFAULT 0 NOT NULL,
    b_unlock_idle           NUMBER(1) DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.host
    ADD CONSTRAINT c_host_pk PRIMARY KEY (pk_host);   
ALTER TABLE cue3.host ADD CONSTRAINT c_host_uk UNIQUE (str_name);
CREATE INDEX i_host_pkalloc ON cue3.host (pk_alloc);
CREATE INDEX i_host_strstate ON cue3.host (str_state);
CREATE INDEX i_host_strlockstate ON cue3.host (str_lock_state);

ALTER TABLE cue3.host ADD CONSTRAINT c_host_pk_alloc
FOREIGN KEY (pk_alloc) REFERENCES alloc (pk_alloc);

drop index i_host_str_tags force;
execute ctx_ddl.drop_index_set('tag_set');
execute ctx_ddl.create_index_set ('tag_set');
execute ctx_ddl.add_index('tag_set','str_name');
create index i_host_str_tags ON host (str_tags) INDEXTYPE IS ctxsys.ctxcat parameters ('INDEX SET tag_set'); 

---


--- Host stats
---
CREATE TABLE cue3.host_stat (  
    pk_host_stat            VARCHAR2(36) NOT NULL,
    pk_host                 VARCHAR2(36) NOT NULL,
    int_mem_total           NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_free            NUMBER(38) DEFAULT 0 NOT NULL,
    int_swap_total          NUMBER(38) DEFAULT 0 NOT NULL,
    int_swap_free           NUMBER(38) DEFAULT 0 NOT NULL,
    int_mcp_total           NUMBER(38) DEFAULT 0 NOT NULL,
    int_mcp_free            NUMBER(38) DEFAULT 0 NOT NULL,
    int_load                NUMBER(38) DEFAULT 0 NOT NULL,
    b_over_loaded           NUMBER(1) DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.host_stat
    ADD CONSTRAINT c_hoststat_pk PRIMARY KEY (pk_host_stat);
ALTER TABLE cue3.host_stat ADD CONSTRAINT c_host_stat_pk_host_uk UNIQUE (pk_host);

ALTER TABLE cue3.host_stat ADD CONSTRAINT c_host_stat_pk_host
FOREIGN KEY (pk_host) REFERENCES host (pk_host);
---

/**
*
* Stores individual host tags
**/
CREATE TABLE cue3.host_tag (
    pk_host_tag            VARCHAR2(36) NOT NULL,
    pk_host                VARCHAR2(36) NOT NULL,
    str_tag                VARCHAR2(36) NOT NULL,
    str_tag_type           VARCHAR2(16) DEFAULT 'Hardware' NOT NULL,
    b_constant             NUMBER(1,0) DEFAULT 0 NOT NULL 
);

ALTER TABLE cue3.host_tag ADD CONSTRAINT c_host_tag_pk PRIMARY KEY (pk_host_tag);
CREATE INDEX i_host_tag_pk_host ON cue3.host_tag (pk_host);
CREATE INDEX i_host_str_tag_type ON cue3.host_tag (str_tag_type);

---

--- 
--- Procs
---
CREATE TABLE cue3.proc (
    pk_proc                 VARCHAR2(36) NOT NULL,
    pk_host                 VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36),
    pk_show                 VARCHAR2(36),  
    pk_layer                VARCHAR2(36),
    pk_frame                VARCHAR2(36),
    int_cores_reserved      NUMBER(38) NOT NULL,
    int_mem_reserved        NUMBER(38) NOT NULL,
    int_mem_used            NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_max_used        NUMBER(38) DEFAULT 0 NOT NULL,
    ts_ping                 TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_booked               TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_disptched            TIMESTAMP DEFAULT systimestamp NOT NULL,
    b_unbooked              NUMBER(1)  DEFAULT 0 NOT NULL
);
---
ALTER TABLE cue3.proc
    ADD CONSTRAINT c_proc_pk PRIMARY KEY (pk_proc);
    
ALTER TABLE cue3.proc
    ADD CONSTRAINT c_proc_uk UNIQUE (pk_frame);

CREATE INDEX i_proc_pkhost ON cue3.proc  (pk_host);
CREATE INDEX i_proc_pkjob ON cue3.proc  (pk_job);
CREATE INDEX i_proc_pklayer ON cue3.proc  (pk_layer);
CREATE INDEX i_proc_pkshow ON cue3.proc  (pk_show);

ALTER TABLE cue3.proc ADD CONSTRAINT c_proc_pk_host
FOREIGN KEY (pk_host) REFERENCES host (pk_host);

ALTER TABLE cue3.proc ADD CONSTRAINT c_proc_pk_frame
FOREIGN KEY (pk_frame) REFERENCES frame (pk_frame);
---

---
--- Frames
---
CREATE TABLE cue3.frame (
---
    pk_frame                VARCHAR2(36) NOT NULL,
    pk_layer                VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    pk_show                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(256) NOT NULL,
    str_state               VARCHAR2(24) NOT NULL,
    int_number              NUMBER(38) NOT NULL,
    int_depend_count        NUMBER(38) DEFAULT 0 NOT NULL,
    int_exit_status         NUMBER(38) DEFAULT -1 NOT NULL,              
    int_retries             NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_reserved        NUMBER(38) DEFAULT 0 NOT NULL,
    int_dispatch_order      NUMBER(38) DEFAULT 0 NOT NULL,
    ts_started              TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_stopped              TIMESTAMP,
    ts_updated              TIMESTAMP,
    str_host                VARCHAR2(265),
    int_mem_max_used        NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_used            NUMBER(38) DEFAULT 0 NOT NULL,
    int_cores               NUMBER(16) DEFAULT 0 NOT NULL
);

ALTER TABLE cue3.frame
    ADD CONSTRAINT c_frame_pk PRIMARY KEY (pk_frame);

ALTER TABLE cue3.frame
    ADD CONSTRAINT c_frame_str_name_unq UNIQUE (str_name, pk_job);
    
CREATE INDEX i_frame_pk_layer ON cue3.frame (pk_layer);
CREATE INDEX i_frame_ts_last_updated ON cue3.frame (ts_updated);
CREATE INDEX i_frame_ts_last_started ON cue3.frame (ts_started);
CREATE INDEX i_frame_ts_last_stopped cue3.frame (ts_stopped);
CREATE INDEX i_frame_intdispatchorder ON cue3.frame (int_dispatch_order);
CREATE INDEX i_frame_str_state ON cue3.frame (str_state);
CREATE INDEX i_frame_int_depend_count ON cue3.frame (int_depend_count);
CREATE INDEX i_frame_pk_job ON cue3.frame (pk_job);


ALTER TABLE cue3.frame ADD CONSTRAINT c_frame_pk_layer
FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);

ALTER TABLE cue3.frame ADD CONSTRAINT c_frame_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);
---


--- 
--- Dependencies
---
CREATE TABLE cue3.depend (
    pk_depend               VARCHAR2(36) NOT NULL,
    pk_parent               VARCHAR2(36),
    pk_job_depend_on        VARCHAR2(36) NOT NULL,
    pk_job_depend_er        VARCHAR2(36) NOT NULL,
    pk_frame_depend_on      VARCHAR2(36),
    pk_frame_depend_er      VARCHAR2(36),
    pk_layer_depend_on      VARCHAR2(36),
    pk_layer_depend_er      VARCHAR2(36),
    str_target              VARCHAR2(20) NOT NULL,
    int_chunk_size          NUMBER(8) DEFAULT 1 NOT NULL,
    str_type                VARCHAR2(36) NOT NULL,
    b_active                NUMBER(1) DEFAULT 1 NOT NULL,
    b_any                   NUMBER(1) DEFAULT 0 NOT NULL,
    ts_created              TIMESTAMP DEFAULT systimestamp NOT NULL,
    ts_satisfied            TIMESTAMP,
    str_signature           VARCHAR2(36) NOT NULL
);
---
ALTER TABLE cue3.depend
    ADD CONSTRAINT c_depend_pk PRIMARY KEY (pk_depend);

CREATE INDEX i_depend_pkparent ON cue3.depend (pk_parent);
CREATE INDEX i_depend_b_active ON cue3.depend (b_active);      
CREATE INDEX i_depend_str_target ON cue3.depend (str_target);

CREATE INDEX i_depend_on_layer ON cue3.depend (pk_job_depend_on, pk_layer_depend_on);
CREATE INDEX i_depend_on_frame ON cue3.depend (pk_job_depend_on, pk_frame_depend_on);
CREATE INDEX i_depend_er_layer ON cue3.depend (pk_job_depend_er, pk_layer_depend_er);
CREATE INDEX i_depend_er_frame ON cue3.depend (pk_job_depend_er, pk_frame_depend_er);

CREATE UNIQUE INDEX c_depend_uniq ON cue3.depend (b_active, pk_signature);

---
--- Allocations
---
CREATE TABLE cue3.alloc (
---
    pk_alloc                VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(36) NOT NULL,
    str_tag                 VARCHAR2(36) NOT NULL,
    b_allow_edit            NUMBER(1) DEFAULT 1 NOT NULL
);
---
ALTER TABLE cue3.alloc
    ADD CONSTRAINT c_alloc_pk PRIMARY KEY (pk_alloc);
    
ALTER TABLE cue3.alloc
    ADD CONSTRAINT c_alloc_name_uniq UNIQUE (str_name);

---

---
--- Subscriptions
---
CREATE table cue3.subscription (
    pk_subscription         VARCHAR2(36) NOT NULL,
    pk_alloc                VARCHAR2(36) NOT NULL,
    pk_show                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(32) NOT NULL,
    int_size                NUMBER(38) DEFAULT 0 NOT NULL,
    int_burst               NUMBER(38) DEFAULT 0 NOT NULL 
);

ALTER TABLE cue3.subscription
    ADD CONSTRAINT c_subscription_pk PRIMARY KEY (pk_subscription);
ALTER TABLE cue3.subscription
    ADD CONSTRAINT c_subscription_uk UNIQUE (pk_show, pk_alloc);

CREATE INDEX i_subscription_pkalloc ON cue3.subscription  (pk_alloc);

ALTER TABLE cue3.subscription ADD CONSTRAINT c_subscription_pk_show
FOREIGN KEY (pk_show) REFERENCES show (pk_show);
       
ALTER TABLE cue3.subscription ADD CONSTRAINT c_subscription_pk_alloc
FOREIGN KEY (pk_alloc) REFERENCES alloc (pk_alloc);

---

---
--- stores the layer usage stats
---
CREATE TABLE cue3.layer_usage (
    pk_layer_usage          VARCHAR2(36) NOT NULL,
    pk_layer                VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_proc_seconds        NUMBER(38) DEFAULT 0 NOT NULL,
    int_proc_seconds_lost   NUMBER(38) DEFAULT 0 NOT NULL
);
  
ALTER TABLE  cue3.layer_usage
    ADD CONSTRAINT c_layer_usage_pk PRIMARY KEY (pk_layer_usage);
ALTER TABLE cue3.layer_usage ADD CONSTRAINT c_layer_usage_pk_layer_uk UNIQUE (pk_layer);

ALTER TABLE cue3.layer_usage ADD CONSTRAINT c_layer_usage_pk_layer
FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);

ALTER TABLE cue3.layer_usage ADD CONSTRAINT c_layer_usage_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);
---


---
--- stores the layer usage stats
---
CREATE TABLE cue3.job_usage (
    pk_job_usage            VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_proc_seconds        NUMBER(38) DEFAULT 0 NOT NULL,
    int_proc_seconds_lost   NUMBER(38) DEFAULT 0 NOT NULL
);
  
ALTER TABLE cue3.job_usage ADD CONSTRAINT c_job_usage_pk PRIMARY KEY (pk_job_usage);
ALTER TABLE cue3.job_usage ADD CONSTRAINT c_job_usage_pk_job_uniq UNIQUE (pk_job);
ALTER TABLE cue3.job_usage ADD CONSTRAINT c_job_usage_pk_job FOREIGN KEY (pk_job) REFERENCES job (pk_job);


---
--- Resources assigned to a layer
---
CREATE TABLE cue3.layer_resource (
    pk_layer_resource       VARCHAR2(36) NOT NULL,
    pk_layer                VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_procs               NUMBER(38) DEFAULT 0 NOT NULL,
    int_cores               NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_reserved        NUMBER(38) DEFAULT 0 NOT NULL
);
ALTER TABLE cue3.layer_resource
    ADD CONSTRAINT c_layerresource_pk PRIMARY KEY (pk_layer_resource);
ALTER TABLE cue3.layer_resource ADD CONSTRAINT c_layerresource_uk UNIQUE (pk_layer);
CREATE INDEX i_layer_resource_pk_job ON cue3.layer_resource (pk_job);

ALTER TABLE cue3.layer_resource ADD CONSTRAINT c_layer_resource_pk_layer
FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);

ALTER TABLE cue3.layer_resource ADD CONSTRAINT c_layer_resource_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);
---

CREATE TABLE cue3.job_resource (
    pk_job_resource         VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_procs               NUMBER(38) DEFAULT 0 NOT NULL,
    int_cores               NUMBER(38) DEFAULT 0 NOT NULL,
    int_mem_reserved        NUMBER(38) DEFAULT 0 NOT NULL
);
ALTER TABLE cue3.job_resource
    ADD CONSTRAINT c_job_resource_pk PRIMARY KEY (pk_job_resource);
ALTER TABLE cue3.job_resource ADD CONSTRAINT c_job_resource_uk UNIQUE (pk_job);
CREATE INDEX i_job_resource_pk_job ON cue3.job_resource (pk_job);
ALTER TABLE cue3.job_resource ADD CONSTRAINT c_job_resource_pk_job FOREIGN KEY (pk_job) REFERENCES job (pk_job);


---
--- Keeps track of the total number of each frame in a particular state.
---
CREATE TABLE cue3.layer_stat (
---
    pk_layer_stat           VARCHAR2(36) NOT NULL,
    pk_layer                VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_total_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_waiting_count       NUMBER(38) DEFAULT 0 NOT NULL,
    int_running_count       NUMBER(38) DEFAULT 0 NOT NULL,
    int_dead_count          NUMBER(38) DEFAULT 0 NOT NULL,
    int_depend_count        NUMBER(38) DEFAULT 0 NOT NULL,
    int_eaten_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_succeeded_count     NUMBER(38) DEFAULT 0 NOT NULL,
    int_reserved_count      NUMBER(38) DEFAULT 0 NOT NULL,
    int_retry_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_stopped_count       NUMBER(38) DEFAULT 0 NOT NULL
);
---    
ALTER TABLE cue3.layer_stat
    ADD CONSTRAINT c_layerstat_pk PRIMARY KEY (pk_layer_stat);

CREATE INDEX i_layerstat_pklayer ON cue3.layer_stat  (pk_layer);
CREATE INDEX i_layerstat_pkjob ON cue3.layer_stat  (pk_job);
CREATE INDEX i_layerstat_int_waiting_count ON cue3.layer_stat  (int_waiting_count);

ALTER TABLE cue3.layer_stat ADD CONSTRAINT c_layer_stat_pk_layer
FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);

ALTER TABLE cue3.layer_stat ADD CONSTRAINT c_layer_stat_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);


CREATE TABLE cue3.job_stat (
---
    pk_job_stat           VARCHAR2(36) NOT NULL,
    pk_job                  VARCHAR2(36) NOT NULL,
    int_total_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_waiting_count       NUMBER(38) DEFAULT 0 NOT NULL,
    int_running_count       NUMBER(38) DEFAULT 0 NOT NULL,
    int_dead_count          NUMBER(38) DEFAULT 0 NOT NULL,
    int_depend_count        NUMBER(38) DEFAULT 0 NOT NULL,
    int_eaten_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_succeeded_count     NUMBER(38) DEFAULT 0 NOT NULL,
    int_reserved_count      NUMBER(38) DEFAULT 0 NOT NULL,
    int_retry_count         NUMBER(38) DEFAULT 0 NOT NULL,
    int_stopped_count       NUMBER(38) DEFAULT 0 NOT NULL
);
---    
ALTER TABLE cue3.job_stat
    ADD CONSTRAINT c_job_stat_pk PRIMARY KEY (pk_job_stat);

CREATE INDEX i_job_stat_pkjob ON cue3.job_stat  (pk_job);
CREATE INDEX i_job_stat_int_waiting_count ON cue3.job_stat  (int_waiting_count);

ALTER TABLE cue3.job_stat ADD CONSTRAINT c_job_stat_pk_job
FOREIGN KEY (pk_job) REFERENCES job (pk_job);

COMMIT;
