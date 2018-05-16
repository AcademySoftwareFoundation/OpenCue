--------------------------------------------------------
--  File created - Friday-January-13-2012   
--------------------------------------------------------
  DROP TABLE "CUE3"."ACTION" cascade constraints;
  DROP TABLE "CUE3"."ALLOC" cascade constraints;
  DROP TABLE "CUE3"."COMMENTS" cascade constraints;
  DROP TABLE "CUE3"."CONFIG" cascade constraints;
  DROP TABLE "CUE3"."DEED" cascade constraints;
  DROP TABLE "CUE3"."DEPEND" cascade constraints;
  DROP TABLE "CUE3"."DEPT" cascade constraints;
  DROP TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" cascade constraints;
  DROP TABLE "CUE3"."DUPLICATE_CURSORS" cascade constraints;
  DROP TABLE "CUE3"."FACILITY" cascade constraints;
  DROP TABLE "CUE3"."FILTER" cascade constraints;
  DROP TABLE "CUE3"."FOLDER" cascade constraints;
  DROP TABLE "CUE3"."FOLDER_LEVEL" cascade constraints;
  DROP TABLE "CUE3"."FOLDER_RESOURCE" cascade constraints;
  DROP TABLE "CUE3"."FRAME" cascade constraints;
  DROP TABLE "CUE3"."FRAME_HISTORY" cascade constraints;
  DROP TABLE "CUE3"."HOST" cascade constraints;
  DROP TABLE "CUE3"."HOST_LOCAL" cascade constraints;
  DROP TABLE "CUE3"."HOST_STAT" cascade constraints;
  DROP TABLE "CUE3"."HOST_TAG" cascade constraints;
  DROP TABLE "CUE3"."JOB" cascade constraints;
  DROP TABLE "CUE3"."JOB_ENV" cascade constraints;
  DROP TABLE "CUE3"."JOB_HISTORY" cascade constraints;
  DROP TABLE "CUE3"."JOB_LOCAL" cascade constraints;
  DROP TABLE "CUE3"."JOB_MEM" cascade constraints;
  DROP TABLE "CUE3"."JOB_POST" cascade constraints;
  DROP TABLE "CUE3"."JOB_RESOURCE" cascade constraints;
  DROP TABLE "CUE3"."JOB_STAT" cascade constraints;
  DROP TABLE "CUE3"."JOB_USAGE" cascade constraints;
  DROP TABLE "CUE3"."LAYER" cascade constraints;
  DROP TABLE "CUE3"."LAYER_ENV" cascade constraints;
  DROP TABLE "CUE3"."LAYER_HISTORY" cascade constraints;
  DROP TABLE "CUE3"."LAYER_MEM" cascade constraints;
  DROP TABLE "CUE3"."LAYER_OUTPUT" cascade constraints;
  DROP TABLE "CUE3"."LAYER_RESOURCE" cascade constraints;
  DROP TABLE "CUE3"."LAYER_STAT" cascade constraints;
  DROP TABLE "CUE3"."LAYER_USAGE" cascade constraints;
  DROP TABLE "CUE3"."MATCHER" cascade constraints;
  DROP TABLE "CUE3"."MATTHEW_STATS_TAB" cascade constraints;
  DROP TABLE "CUE3"."OWNER" cascade constraints;
  DROP TABLE "CUE3"."POINT" cascade constraints;
  DROP TABLE "CUE3"."PROC" cascade constraints;
  DROP TABLE "CUE3"."SERVICE" cascade constraints;
  DROP TABLE "CUE3"."SHOW" cascade constraints;
  DROP TABLE "CUE3"."SHOW_ALIAS" cascade constraints;
  DROP TABLE "CUE3"."SHOW_SERVICE" cascade constraints;
  DROP TABLE "CUE3"."SQLN_EXPLAIN_PLAN" cascade constraints;
  DROP TABLE "CUE3"."SUBSCRIPTION" cascade constraints;
  DROP TABLE "CUE3"."TASK" cascade constraints;
  DROP TABLE "CUE3"."TASK_LOCK" cascade constraints;
  DROP TABLE "CUE3"."TEST" cascade constraints;
  DROP TABLE "CUE3"."UNCOMMITTED_TRANSACTIONS" cascade constraints;
  DROP TABLE "CUE3"."UNCOMMITTED_TRANSACTIONS_BAK" cascade constraints;
  DROP SEQUENCE "CUE3"."THREAD_SEQ";
  DROP VIEW "CUE3"."VS_ALLOC_USAGE";
  DROP VIEW "CUE3"."VS_FOLDER_COUNTS";
  DROP VIEW "CUE3"."VS_JOB_RESOURCE";
  DROP VIEW "CUE3"."VS_SHOW_RESOURCE";
  DROP VIEW "CUE3"."VS_SHOW_STAT";
  DROP VIEW "CUE3"."VS_WAITING";
  DROP FUNCTION "CUE3"."CALCULATE_CORE_HOURS";
  DROP FUNCTION "CUE3"."EPOCH";
  DROP FUNCTION "CUE3"."EPOCH_TO_TS";
  DROP FUNCTION "CUE3"."FIND_DURATION";
  DROP FUNCTION "CUE3"."GENKEY";
  DROP FUNCTION "CUE3"."INTERVAL_TO_SECONDS";
  DROP FUNCTION "CUE3"."RENDER_WEEKS";
  DROP FUNCTION "CUE3"."SOFT_TIER";
  DROP FUNCTION "CUE3"."TIER";
  DROP PROCEDURE "CUE3"."RECALCULATE_SUBS";
  DROP PROCEDURE "CUE3"."RECALCULATE_TAGS";
  DROP PROCEDURE "CUE3"."RECURSE_FOLDER_PARENT_CHANGE";
  DROP PROCEDURE "CUE3"."RENAME_ALLOCS";
  DROP PROCEDURE "CUE3"."REORDER_FILTERS";
  DROP PROCEDURE "CUE3"."TMP_POPULATE_FOLDER";
  DROP PROCEDURE "CUE3"."TMP_POPULATE_POINT";
  DROP PROCEDURE "CUE3"."TMP_POPULATE_SUB";
  DROP TYPE "CUE3"."NLIST";
--------------------------------------------------------
--  DDL for Type NLIST
--------------------------------------------------------

  CREATE OR REPLACE TYPE "CUE3"."NLIST" AS VARRAY(32) OF NUMBER(1,0);
  

/

--------------------------------------------------------
--  DDL for Sequence THREAD_SEQ
--------------------------------------------------------

   CREATE SEQUENCE  "CUE3"."THREAD_SEQ"  MINVALUE 1 MAXVALUE 999999999999999999999999999 INCREMENT BY 1 START WITH 26151 CACHE 20 NOORDER  NOCYCLE ;
--------------------------------------------------------
--  DDL for Table FILTER
--------------------------------------------------------

  CREATE TABLE "CUE3"."FILTER" 
   (	"PK_FILTER" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(128), 
	"STR_TYPE" VARCHAR2(16), 
	"F_ORDER" NUMBER(6,2) DEFAULT 0.0, 
	"B_ENABLED" NUMBER(1,0) DEFAULT 1
   ) ;
--------------------------------------------------------
--  DDL for Table FOLDER
--------------------------------------------------------

  CREATE TABLE "CUE3"."FOLDER" 
   (	"PK_FOLDER" VARCHAR2(36), 
	"PK_PARENT_FOLDER" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"INT_PRIORITY" NUMBER(38,0) DEFAULT 1, 
	"B_DEFAULT" NUMBER(1,0) DEFAULT 0, 
	"PK_DEPT" VARCHAR2(36), 
	"INT_JOB_MIN_CORES" NUMBER(16,0) DEFAULT -1, 
	"INT_JOB_MAX_CORES" NUMBER(16,0) DEFAULT -1, 
	"INT_JOB_PRIORITY" NUMBER(16,0) DEFAULT -1, 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_CORES" NUMBER(16,0) DEFAULT -1, 
	"B_EXCLUDE_MANAGED" NUMBER(1,0) DEFAULT 0, 
	"F_ORDER" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table ACTION
--------------------------------------------------------

  CREATE TABLE "CUE3"."ACTION" 
   (	"PK_ACTION" VARCHAR2(36), 
	"PK_FILTER" VARCHAR2(36), 
	"PK_FOLDER" VARCHAR2(36), 
	"STR_ACTION" VARCHAR2(24), 
	"STR_VALUE_TYPE" VARCHAR2(24), 
	"STR_VALUE" VARCHAR2(4000), 
	"INT_VALUE" NUMBER(38,0), 
	"B_VALUE" NUMBER(1,0), 
	"TS_CREATED" TIMESTAMP (6) DEFAULT systimestamp, 
	"FLOAT_VALUE" NUMBER(6,2), 
	"B_STOP" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table FACILITY
--------------------------------------------------------

  CREATE TABLE "CUE3"."FACILITY" 
   (	"PK_FACILITY" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_DEFAULT" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table ALLOC
--------------------------------------------------------

  CREATE TABLE "CUE3"."ALLOC" 
   (	"PK_ALLOC" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_ALLOW_EDIT" NUMBER(1,0) DEFAULT 1, 
	"B_DEFAULT" NUMBER(1,0) DEFAULT 0, 
	"STR_TAG" VARCHAR2(24), 
	"B_BILLABLE" NUMBER(1,0) DEFAULT 1, 
	"PK_FACILITY" VARCHAR2(36), 
	"B_ENABLED" NUMBER(1,0) DEFAULT 1
   ) ;
--------------------------------------------------------
--  DDL for Table HOST
--------------------------------------------------------

  CREATE TABLE "CUE3"."HOST" 
   (	"PK_HOST" VARCHAR2(36), 
	"PK_ALLOC" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(30), 
	"STR_LOCK_STATE" VARCHAR2(36), 
	"B_NIMBY" NUMBER(1,0) DEFAULT 0, 
	"TS_CREATED" TIMESTAMP (6) DEFAULT systimestamp, 
	"INT_CORES" NUMBER(38,0) DEFAULT 0, 
	"INT_PROCS" NUMBER(38,0) DEFAULT 0, 
	"INT_CORES_IDLE" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_IDLE" NUMBER(38,0) DEFAULT 0, 
	"B_UNLOCK_BOOT" NUMBER(1,0) DEFAULT 0, 
	"B_UNLOCK_IDLE" NUMBER(1,0) DEFAULT 0, 
	"B_REBOOT_IDLE" NUMBER(1,0) DEFAULT 0, 
	"STR_TAGS" VARCHAR2(128), 
	"STR_FQDN" VARCHAR2(128), 
	"B_COMMENT" NUMBER(1,0) DEFAULT 0, 
	"INT_THREAD_MODE" NUMBER(1,0) DEFAULT 0, 
	"STR_LOCK_SOURCE" VARCHAR2(128), 
	"INT_GPU" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_IDLE" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB" 
   (	"PK_JOB" VARCHAR2(36), 
	"PK_FOLDER" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(255), 
	"STR_VISIBLE_NAME" VARCHAR2(255), 
	"STR_SHOT" VARCHAR2(32), 
	"STR_USER" VARCHAR2(32), 
	"STR_STATE" VARCHAR2(16), 
	"STR_LOG_DIR" VARCHAR2(4000) DEFAULT '', 
	"INT_UID" NUMBER(38,0) DEFAULT 0, 
	"B_PAUSED" NUMBER(1,0) DEFAULT 0, 
	"B_AUTOEAT" NUMBER(1,0) DEFAULT 0, 
	"INT_FRAME_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_LAYER_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_RETRIES" NUMBER(4,0) DEFAULT 3, 
	"B_AUTO_BOOK" NUMBER(1,0) DEFAULT 1, 
	"B_AUTO_UNBOOK" NUMBER(1,0) DEFAULT 1, 
	"B_COMMENT" NUMBER(1,0) DEFAULT 0, 
	"STR_EMAIL" VARCHAR2(256), 
	"PK_FACILITY" VARCHAR2(36), 
	"PK_DEPT" VARCHAR2(36), 
	"TS_STARTED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"TS_STOPPED" TIMESTAMP (6) WITH TIME ZONE, 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 100, 
	"INT_MAX_CORES" NUMBER(16,0) DEFAULT 20000, 
	"STR_SHOW" VARCHAR2(32) DEFAULT 'none', 
	"TS_UPDATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"STR_OS" VARCHAR2(12) DEFAULT 'rhel40'
   )  ENABLE ROW MOVEMENT ;
--------------------------------------------------------
--  DDL for Table COMMENTS
--------------------------------------------------------

  CREATE TABLE "CUE3"."COMMENTS" 
   (	"PK_COMMENT" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"TS_CREATED" TIMESTAMP (6) DEFAULT systimestamp, 
	"STR_USER" VARCHAR2(36), 
	"STR_SUBJECT" VARCHAR2(128), 
	"STR_MESSAGE" VARCHAR2(4000)
   ) ;
--------------------------------------------------------
--  DDL for Table CONFIG
--------------------------------------------------------

  CREATE TABLE "CUE3"."CONFIG" 
   (	"PK_CONFIG" VARCHAR2(36), 
	"STR_KEY" VARCHAR2(36), 
	"INT_VALUE" NUMBER(38,0) DEFAULT 0, 
	"LONG_VALUE" NUMBER(38,0) DEFAULT 0, 
	"STR_VALUE" VARCHAR2(255) DEFAULT '', 
	"B_VALUE" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table DEED
--------------------------------------------------------

  CREATE TABLE "CUE3"."DEED" 
   (	"PK_DEED" VARCHAR2(36), 
	"PK_OWNER" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"B_BLACKOUT" NUMBER(1,0) DEFAULT 0, 
	"INT_BLACKOUT_START" NUMBER(12,0), 
	"INT_BLACKOUT_STOP" NUMBER(12,0)
   ) ;
--------------------------------------------------------
--  DDL for Table DEPEND
--------------------------------------------------------

  CREATE TABLE "CUE3"."DEPEND" 
   (	"PK_DEPEND" VARCHAR2(36), 
	"PK_PARENT" VARCHAR2(36), 
	"PK_JOB_DEPEND_ON" VARCHAR2(36), 
	"PK_JOB_DEPEND_ER" VARCHAR2(36), 
	"PK_FRAME_DEPEND_ON" VARCHAR2(36), 
	"PK_FRAME_DEPEND_ER" VARCHAR2(36), 
	"PK_LAYER_DEPEND_ON" VARCHAR2(36), 
	"PK_LAYER_DEPEND_ER" VARCHAR2(36), 
	"STR_TYPE" VARCHAR2(36), 
	"B_ACTIVE" NUMBER(1,0) DEFAULT 1, 
	"B_ANY" NUMBER(1,0) DEFAULT 0, 
	"TS_CREATED" TIMESTAMP (6) DEFAULT systimestamp, 
	"TS_SATISFIED" TIMESTAMP (6), 
	"STR_TARGET" VARCHAR2(20) DEFAULT 'Internal', 
	"STR_SIGNATURE" VARCHAR2(36), 
	"B_COMPOSITE" NUMBER(1,0) DEFAULT 0
   )  ENABLE ROW MOVEMENT ;
--------------------------------------------------------
--  DDL for Table DEPT
--------------------------------------------------------

  CREATE TABLE "CUE3"."DEPT" 
   (	"PK_DEPT" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_DEFAULT" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table DR$I_HOST_STR_TAGS$I
--------------------------------------------------------

  CREATE TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" 
   (	"DR$TOKEN" VARCHAR2(64), 
	"DR$TOKEN_TYPE" NUMBER(3,0), 
	"DR$ROWID" ROWID, 
	"DR$TOKEN_INFO" RAW(2000), 
	"STR_NAME" VARCHAR2(30)
   ) ;
--------------------------------------------------------
--  DDL for Table SHOW
--------------------------------------------------------

  CREATE TABLE "CUE3"."SHOW" 
   (	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_PAUSED" NUMBER(1,0) DEFAULT 0, 
	"INT_DEFAULT_MIN_CORES" NUMBER(16,0) DEFAULT 100, 
	"INT_DEFAULT_MAX_CORES" NUMBER(16,0) DEFAULT 10000, 
	"INT_FRAME_INSERT_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_JOB_INSERT_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_SUCCESS_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_FAIL_COUNT" NUMBER(38,0) DEFAULT 0, 
	"B_BOOKING_ENABLED" NUMBER(1,0) DEFAULT 1, 
	"B_DISPATCH_ENABLED" NUMBER(1,0) DEFAULT 1, 
	"B_ACTIVE" NUMBER(1,0) DEFAULT 1, 
	"STR_COMMENT_EMAIL" VARCHAR2(1024)
   ) ;
--------------------------------------------------------
--  DDL for Table DUPLICATE_CURSORS
--------------------------------------------------------

  CREATE TABLE "CUE3"."DUPLICATE_CURSORS" 
   (	"DT_RECORDED" DATE, 
	"INST_ID" NUMBER, 
	"LNG_COUNT" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table FOLDER_LEVEL
--------------------------------------------------------

  CREATE TABLE "CUE3"."FOLDER_LEVEL" 
   (	"PK_FOLDER_LEVEL" VARCHAR2(36), 
	"PK_FOLDER" VARCHAR2(36), 
	"INT_LEVEL" NUMBER(38,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table FOLDER_RESOURCE
--------------------------------------------------------

  CREATE TABLE "CUE3"."FOLDER_RESOURCE" 
   (	"PK_FOLDER_RESOURCE" VARCHAR2(36), 
	"PK_FOLDER" VARCHAR2(36), 
	"INT_CORES" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_CORES" NUMBER(16,0) DEFAULT -1, 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 0, 
	"FLOAT_TIER" NUMBER(16,2) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER" 
   (	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(256), 
	"STR_CMD" VARCHAR2(4000), 
	"STR_RANGE" VARCHAR2(4000), 
	"INT_CHUNK_SIZE" NUMBER(38,0) DEFAULT 1, 
	"INT_DISPATCH_ORDER" NUMBER(38,0) DEFAULT 1, 
	"INT_CORES_MIN" NUMBER(38,0) DEFAULT 100, 
	"INT_MEM_MIN" NUMBER(38,0) DEFAULT 4194304, 
	"STR_TAGS" VARCHAR2(4000) DEFAULT '', 
	"STR_TYPE" VARCHAR2(16), 
	"B_THREADABLE" NUMBER(1,0) DEFAULT 1, 
	"STR_SERVICES" VARCHAR2(128) DEFAULT 'default', 
	"B_OPTIMIZE" NUMBER(1,0) DEFAULT 1, 
	"INT_CORES_MAX" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_MIN" NUMBER(10,0) DEFAULT 0
   )  ENABLE ROW MOVEMENT ;
--------------------------------------------------------
--  DDL for Table FRAME
--------------------------------------------------------

  CREATE TABLE "CUE3"."FRAME" 
   (	"PK_FRAME" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(256), 
	"STR_STATE" VARCHAR2(24), 
	"INT_NUMBER" NUMBER(38,0), 
	"INT_DEPEND_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_EXIT_STATUS" NUMBER(38,0) DEFAULT -1, 
	"INT_RETRIES" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_RESERVED" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_MAX_USED" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_USED" NUMBER(38,0) DEFAULT 0, 
	"INT_DISPATCH_ORDER" NUMBER(38,0) DEFAULT 0, 
	"STR_HOST" VARCHAR2(256), 
	"INT_CORES" NUMBER(16,0) DEFAULT 0, 
	"INT_LAYER_ORDER" NUMBER(16,0), 
	"TS_STARTED" TIMESTAMP (6) WITH TIME ZONE, 
	"TS_STOPPED" TIMESTAMP (6) WITH TIME ZONE, 
	"TS_LAST_RUN" TIMESTAMP (6) WITH TIME ZONE, 
	"TS_UPDATED" TIMESTAMP (6) WITH TIME ZONE, 
	"INT_VERSION" NUMBER(16,0) DEFAULT 0, 
	"STR_CHECKPOINT_STATE" VARCHAR2(12) DEFAULT 'Disabled', 
	"INT_CHECKPOINT_COUNT" NUMBER(6,0) DEFAULT 0, 
	"INT_GPU_RESERVED" NUMBER(10,0) DEFAULT 0, 
	"INT_TOTAL_PAST_CORE_TIME" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_HISTORY
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_HISTORY" 
   (	"PK_JOB" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(512), 
	"STR_SHOT" VARCHAR2(36), 
	"STR_USER" VARCHAR2(36), 
	"INT_CORE_TIME_SUCCESS" NUMBER(38,0) DEFAULT 0, 
	"INT_CORE_TIME_FAIL" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_LAYER_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_WAITING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEAD_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEPEND_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_EATEN_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_SUCCEEDED_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_RUNNING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_MAX_RSS" NUMBER(38,0) DEFAULT 0, 
	"B_ARCHIVED" NUMBER(1,0) DEFAULT 0, 
	"PK_FACILITY" VARCHAR2(36), 
	"PK_DEPT" VARCHAR2(36), 
	"INT_TS_STARTED" NUMBER(12,0), 
	"INT_TS_STOPPED" NUMBER(12,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_HISTORY
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_HISTORY" 
   (	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(512), 
	"STR_TYPE" VARCHAR2(16), 
	"INT_CORES_MIN" NUMBER(38,0) DEFAULT 100, 
	"INT_MEM_MIN" NUMBER(38,0) DEFAULT 4194304, 
	"INT_CORE_TIME_SUCCESS" NUMBER(38,0) DEFAULT 0, 
	"INT_CORE_TIME_FAIL" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_LAYER_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_WAITING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEAD_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEPEND_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_EATEN_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_SUCCEEDED_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_RUNNING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_MAX_RSS" NUMBER(38,0) DEFAULT 0, 
	"B_ARCHIVED" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table FRAME_HISTORY
--------------------------------------------------------

  CREATE TABLE "CUE3"."FRAME_HISTORY" 
   (	"PK_FRAME_HISTORY" RAW(16) DEFAULT sys_guid(), 
	"PK_FRAME" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(256), 
	"STR_STATE" VARCHAR2(24), 
	"INT_MEM_RESERVED" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_MAX_USED" NUMBER(38,0) DEFAULT 0, 
	"INT_CORES" NUMBER(16,0) DEFAULT 100, 
	"STR_HOST" VARCHAR2(64) DEFAULT NULL, 
	"INT_EXIT_STATUS" NUMBER(8,0) DEFAULT -1, 
	"PK_ALLOC" VARCHAR2(36), 
	"INT_TS_STARTED" NUMBER(12,0), 
	"INT_TS_STOPPED" NUMBER(12,0) DEFAULT 0, 
	"INT_CHECKPOINT_COUNT" NUMBER(6,0) DEFAULT 0
   )  ENABLE ROW MOVEMENT ;
--------------------------------------------------------
--  DDL for Table HOST_LOCAL
--------------------------------------------------------

  CREATE TABLE "CUE3"."HOST_LOCAL" 
   (	"PK_HOST_LOCAL" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_FRAME" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"TS_CREATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT SYSTIMESTAMP, 
	"TS_UPDATED" TIMESTAMP (6) WITH TIME ZONE, 
	"INT_MEM_MAX" NUMBER(16,0) DEFAULT 0, 
	"INT_MEM_IDLE" NUMBER(16,0) DEFAULT 0, 
	"INT_CORES_MAX" NUMBER(16,0) DEFAULT 100, 
	"INT_CORES_IDLE" NUMBER(16,0) DEFAULT 100, 
	"INT_THREADS" NUMBER(4,0) DEFAULT 1, 
	"FLOAT_TIER" NUMBER(16,2) DEFAULT 0, 
	"B_ACTIVE" NUMBER(1,0) DEFAULT 1, 
	"STR_TYPE" VARCHAR2(36), 
	"INT_GPU_IDLE" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_MAX" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table HOST_STAT
--------------------------------------------------------

  CREATE TABLE "CUE3"."HOST_STAT" 
   (	"PK_HOST_STAT" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"INT_MEM_TOTAL" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_FREE" NUMBER(38,0) DEFAULT 0, 
	"INT_SWAP_TOTAL" NUMBER(38,0) DEFAULT 0, 
	"INT_SWAP_FREE" NUMBER(38,0) DEFAULT 0, 
	"INT_MCP_TOTAL" NUMBER(38,0) DEFAULT 0, 
	"INT_MCP_FREE" NUMBER(38,0) DEFAULT 0, 
	"INT_LOAD" NUMBER(38,0) DEFAULT 0, 
	"TS_PING" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"TS_BOOTED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"STR_STATE" VARCHAR2(32) DEFAULT 'Up', 
	"STR_OS" VARCHAR2(12) DEFAULT 'rhel40', 
	"INT_GPU_TOTAL" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_FREE" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table HOST_TAG
--------------------------------------------------------

  CREATE TABLE "CUE3"."HOST_TAG" 
   (	"PK_HOST_TAG" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"STR_TAG" VARCHAR2(36), 
	"STR_TAG_TYPE" VARCHAR2(24) DEFAULT 'Hardware', 
	"B_CONSTANT" NUMBER(1,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_ENV
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_ENV" 
   (	"PK_JOB_ENV" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_KEY" VARCHAR2(36), 
	"STR_VALUE" VARCHAR2(2048)
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_LOCAL
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_LOCAL" 
   (	"PK_JOB_LOCAL" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"STR_SOURCE" VARCHAR2(255), 
	"TS_CREATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT SYSTIMESTAMP, 
	"INT_CORES" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_CORES" NUMBER(16,0)
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_MEM
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_MEM" 
   (	"PK_JOB_MEM" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_MAX_RSS" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_VSS" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_POST
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_POST" 
   (	"PK_JOB_POST" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_POST_JOB" VARCHAR2(36)
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_RESOURCE
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_RESOURCE" 
   (	"PK_JOB_RESOURCE" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_CORES" NUMBER(38,0) DEFAULT 0, 
	"INT_MAX_RSS" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_VSS" NUMBER(16,0) DEFAULT 0, 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 100, 
	"INT_MAX_CORES" NUMBER(16,0) DEFAULT 10000, 
	"FLOAT_TIER" NUMBER(16,2) DEFAULT 0, 
	"INT_PRIORITY" NUMBER(16,0) DEFAULT 1, 
	"INT_LOCAL_CORES" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_STAT
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_STAT" 
   (	"PK_JOB_STAT" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_WAITING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_RUNNING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEAD_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEPEND_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_EATEN_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_SUCCEEDED_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_CHECKPOINT_COUNT" NUMBER(38,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table JOB_USAGE
--------------------------------------------------------

  CREATE TABLE "CUE3"."JOB_USAGE" 
   (	"PK_JOB_USAGE" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_CORE_TIME_SUCCESS" NUMBER(38,0) DEFAULT 0, 
	"INT_CORE_TIME_FAIL" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_SUCCESS_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_FRAME_FAIL_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_FAIL" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_HIGH" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_SUCCESS" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_ENV
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_ENV" 
   (	"PK_LAYER_ENV" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_KEY" VARCHAR2(36), 
	"STR_VALUE" VARCHAR2(2048)
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_MEM
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_MEM" 
   (	"PK_LAYER_MEM" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"INT_MAX_RSS" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_VSS" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_OUTPUT
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_OUTPUT" 
   (	"PK_LAYER_OUTPUT" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"STR_FILESPEC" VARCHAR2(2048)
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_RESOURCE
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_RESOURCE" 
   (	"PK_LAYER_RESOURCE" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_CORES" NUMBER(38,0) DEFAULT 0, 
	"INT_MAX_RSS" NUMBER(16,0) DEFAULT 0, 
	"INT_MAX_VSS" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_STAT
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_STAT" 
   (	"PK_LAYER_STAT" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_TOTAL_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_WAITING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_RUNNING_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEAD_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_DEPEND_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_EATEN_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_SUCCEEDED_COUNT" NUMBER(38,0) DEFAULT 0, 
	"INT_CHECKPOINT_COUNT" NUMBER(38,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table LAYER_USAGE
--------------------------------------------------------

  CREATE TABLE "CUE3"."LAYER_USAGE" 
   (	"PK_LAYER_USAGE" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"INT_CORE_TIME_SUCCESS" NUMBER(38,0) DEFAULT 0, 
	"INT_CORE_TIME_FAIL" NUMBER(38,0) DEFAULT 0, 
	"INT_FRAME_SUCCESS_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_FRAME_FAIL_COUNT" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_FAIL" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_HIGH" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_LOW" NUMBER(16,0) DEFAULT 0, 
	"INT_CLOCK_TIME_SUCCESS" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table MATCHER
--------------------------------------------------------

  CREATE TABLE "CUE3"."MATCHER" 
   (	"PK_MATCHER" VARCHAR2(36), 
	"PK_FILTER" VARCHAR2(36), 
	"STR_SUBJECT" VARCHAR2(64), 
	"STR_MATCH" VARCHAR2(64), 
	"STR_VALUE" VARCHAR2(4000), 
	"TS_CREATED" TIMESTAMP (6) DEFAULT systimestamp
   ) ;
--------------------------------------------------------
--  DDL for Table MATTHEW_STATS_TAB
--------------------------------------------------------

  CREATE TABLE "CUE3"."MATTHEW_STATS_TAB" 
   (	"STATID" VARCHAR2(30), 
	"TYPE" CHAR(1), 
	"VERSION" NUMBER, 
	"FLAGS" NUMBER, 
	"C1" VARCHAR2(30), 
	"C2" VARCHAR2(30), 
	"C3" VARCHAR2(30), 
	"C4" VARCHAR2(30), 
	"C5" VARCHAR2(30), 
	"N1" NUMBER, 
	"N2" NUMBER, 
	"N3" NUMBER, 
	"N4" NUMBER, 
	"N5" NUMBER, 
	"N6" NUMBER, 
	"N7" NUMBER, 
	"N8" NUMBER, 
	"N9" NUMBER, 
	"N10" NUMBER, 
	"N11" NUMBER, 
	"N12" NUMBER, 
	"D1" DATE, 
	"R1" RAW(32), 
	"R2" RAW(32), 
	"CH1" VARCHAR2(1000)
   ) ;
--------------------------------------------------------
--  DDL for Table OWNER
--------------------------------------------------------

  CREATE TABLE "CUE3"."OWNER" 
   (	"PK_OWNER" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_USERNAME" VARCHAR2(64), 
	"TS_CREATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT SYSTIMESTAMP, 
	"TS_UPDATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT SYSTIMESTAMP
   ) ;
--------------------------------------------------------
--  DDL for Table POINT
--------------------------------------------------------

  CREATE TABLE "CUE3"."POINT" 
   (	"PK_POINT" VARCHAR2(36), 
	"PK_DEPT" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_TI_TASK" VARCHAR2(36), 
	"INT_CORES" NUMBER(16,0) DEFAULT 0, 
	"B_MANAGED" NUMBER(1,0) DEFAULT 0, 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 0, 
	"FLOAT_TIER" NUMBER(16,2) DEFAULT 0, 
	"TS_UPDATED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp
   ) ;
--------------------------------------------------------
--  DDL for Table PROC
--------------------------------------------------------

  CREATE TABLE "CUE3"."PROC" 
   (	"PK_PROC" VARCHAR2(36), 
	"PK_HOST" VARCHAR2(36), 
	"PK_JOB" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"PK_LAYER" VARCHAR2(36), 
	"PK_FRAME" VARCHAR2(36), 
	"INT_CORES_RESERVED" NUMBER(38,0), 
	"INT_MEM_RESERVED" NUMBER(38,0), 
	"INT_MEM_USED" NUMBER(38,0) DEFAULT 0, 
	"INT_MEM_MAX_USED" NUMBER(38,0) DEFAULT 0, 
	"B_UNBOOKED" NUMBER(1,0) DEFAULT 0, 
	"INT_MEM_PRE_RESERVED" NUMBER(38,0) DEFAULT 0, 
	"INT_VIRT_USED" NUMBER(16,0) DEFAULT 0, 
	"INT_VIRT_MAX_USED" NUMBER(16,0) DEFAULT 0, 
	"STR_REDIRECT" VARCHAR2(265), 
	"B_LOCAL" NUMBER(1,0) DEFAULT 0, 
	"TS_PING" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"TS_BOOKED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"TS_DISPATCHED" TIMESTAMP (6) WITH TIME ZONE DEFAULT systimestamp, 
	"INT_GPU_RESERVED" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table SERVICE
--------------------------------------------------------

  CREATE TABLE "CUE3"."SERVICE" 
   (	"PK_SERVICE" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_THREADABLE" NUMBER(1,0), 
	"INT_CORES_MIN" NUMBER(8,0), 
	"INT_MEM_MIN" NUMBER(16,0), 
	"STR_TAGS" VARCHAR2(128), 
	"INT_CORES_MAX" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_MIN" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table SHOW_ALIAS
--------------------------------------------------------

  CREATE TABLE "CUE3"."SHOW_ALIAS" 
   (	"PK_SHOW_ALIAS" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(16)
   ) ;
--------------------------------------------------------
--  DDL for Table SHOW_SERVICE
--------------------------------------------------------

  CREATE TABLE "CUE3"."SHOW_SERVICE" 
   (	"PK_SHOW_SERVICE" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"B_THREADABLE" NUMBER(1,0), 
	"INT_CORES_MIN" NUMBER(8,0), 
	"INT_MEM_MIN" NUMBER(16,0), 
	"STR_TAGS" VARCHAR2(128), 
	"INT_CORES_MAX" NUMBER(10,0) DEFAULT 0, 
	"INT_GPU_MIN" NUMBER(10,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table SQLN_EXPLAIN_PLAN
--------------------------------------------------------

  CREATE TABLE "CUE3"."SQLN_EXPLAIN_PLAN" 
   (	"STATEMENT_ID" VARCHAR2(30), 
	"TIMESTAMP" DATE, 
	"REMARKS" VARCHAR2(80), 
	"OPERATION" VARCHAR2(30), 
	"OPTIONS" VARCHAR2(30), 
	"OBJECT_NODE" VARCHAR2(128), 
	"OBJECT_OWNER" VARCHAR2(30), 
	"OBJECT_NAME" VARCHAR2(30), 
	"OBJECT_INSTANCE" NUMBER(*,0), 
	"OBJECT_TYPE" VARCHAR2(30), 
	"OPTIMIZER" VARCHAR2(255), 
	"SEARCH_COLUMNS" NUMBER(*,0), 
	"ID" NUMBER(*,0), 
	"PARENT_ID" NUMBER(*,0), 
	"POSITION" NUMBER(*,0), 
	"COST" NUMBER(*,0), 
	"CARDINALITY" NUMBER(*,0), 
	"BYTES" NUMBER(*,0), 
	"OTHER_TAG" VARCHAR2(255), 
	"PARTITION_START" VARCHAR2(255), 
	"PARTITION_STOP" VARCHAR2(255), 
	"PARTITION_ID" NUMBER(*,0), 
	"OTHER" LONG, 
	"DISTRIBUTION" VARCHAR2(30)
   ) ;
  GRANT UPDATE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT DELETE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT INSERT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT SELECT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;

--------------------------------------------------------
--  DDL for Table SUBSCRIPTION
--------------------------------------------------------

  CREATE TABLE "CUE3"."SUBSCRIPTION" 
   (	"PK_SUBSCRIPTION" VARCHAR2(36), 
	"PK_ALLOC" VARCHAR2(36), 
	"PK_SHOW" VARCHAR2(36), 
	"INT_SIZE" NUMBER(38,0) DEFAULT 0, 
	"INT_BURST" NUMBER(38,0) DEFAULT 0, 
	"INT_CORES" NUMBER(16,0) DEFAULT 0, 
	"FLOAT_TIER" NUMBER(16,2) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table TASK
--------------------------------------------------------

  CREATE TABLE "CUE3"."TASK" 
   (	"PK_TASK" VARCHAR2(36), 
	"PK_POINT" VARCHAR2(36), 
	"STR_SHOT" VARCHAR2(36), 
	"INT_MIN_CORES" NUMBER(16,0) DEFAULT 100, 
	"INT_ADJUST_CORES" NUMBER(16,0) DEFAULT 0
   ) ;
--------------------------------------------------------
--  DDL for Table TASK_LOCK
--------------------------------------------------------

  CREATE TABLE "CUE3"."TASK_LOCK" 
   (	"PK_TASK_LOCK" VARCHAR2(36), 
	"STR_NAME" VARCHAR2(36), 
	"INT_LOCK" NUMBER(38,0) DEFAULT 0, 
	"INT_TIMEOUT" NUMBER(38,0) DEFAULT 30, 
	"TS_LASTRUN" TIMESTAMP (6) DEFAULT systimestamp
   ) ;
--------------------------------------------------------
--  DDL for Table TEST
--------------------------------------------------------

  CREATE TABLE "CUE3"."TEST" 
   (	"COL1" VARCHAR2(32)
   ) ;
--------------------------------------------------------
--  DDL for Table UNCOMMITTED_TRANSACTIONS
--------------------------------------------------------

  CREATE TABLE "CUE3"."UNCOMMITTED_TRANSACTIONS" 
   (	"INST_ID" NUMBER, 
	"SID" NUMBER, 
	"SERIAL#" NUMBER, 
	"USERNAME" VARCHAR2(30), 
	"MACHINE" VARCHAR2(64), 
	"MODULE" VARCHAR2(48), 
	"SERVICE_NAME" VARCHAR2(64), 
	"DURATION" NUMBER, 
	"DT_RECORDED" DATE DEFAULT sysdate
   ) ;
--------------------------------------------------------
--  DDL for Table UNCOMMITTED_TRANSACTIONS_BAK
--------------------------------------------------------

  CREATE TABLE "CUE3"."UNCOMMITTED_TRANSACTIONS_BAK" 
   (	"INST_ID" NUMBER, 
	"SID" NUMBER, 
	"SERIAL#" NUMBER, 
	"USERNAME" VARCHAR2(30), 
	"MACHINE" VARCHAR2(64), 
	"MODULE" VARCHAR2(48), 
	"SERVICE_NAME" VARCHAR2(64), 
	"DURATION" NUMBER, 
	"DT_RECORDED" DATE
   ) ;
--------------------------------------------------------
--  Constraints for Table ACTION
--------------------------------------------------------

  ALTER TABLE "CUE3"."ACTION" MODIFY ("B_STOP" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" MODIFY ("STR_VALUE_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" MODIFY ("STR_ACTION" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" MODIFY ("PK_FILTER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" MODIFY ("PK_ACTION" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ACTION" ADD CONSTRAINT "C_ACTION_PK" PRIMARY KEY ("PK_ACTION") ENABLE;
--------------------------------------------------------
--  Constraints for Table ALLOC
--------------------------------------------------------

  ALTER TABLE "CUE3"."ALLOC" MODIFY ("PK_FACILITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" MODIFY ("B_BILLABLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" MODIFY ("B_DEFAULT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" MODIFY ("B_ALLOW_EDIT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" MODIFY ("PK_ALLOC" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."ALLOC" ADD CONSTRAINT "C_ALLOC_PK" PRIMARY KEY ("PK_ALLOC") ENABLE;
  ALTER TABLE "CUE3"."ALLOC" ADD CONSTRAINT "C_ALLOC_NAME_UNIQ" UNIQUE ("STR_NAME") ENABLE;
--------------------------------------------------------
--  Constraints for Table COMMENTS
--------------------------------------------------------

  ALTER TABLE "CUE3"."COMMENTS" MODIFY ("STR_MESSAGE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."COMMENTS" MODIFY ("STR_SUBJECT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."COMMENTS" MODIFY ("STR_USER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."COMMENTS" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."COMMENTS" MODIFY ("PK_COMMENT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."COMMENTS" ADD CONSTRAINT "C_COMMENT_PK" PRIMARY KEY ("PK_COMMENT") ENABLE;
--------------------------------------------------------
--  Constraints for Table CONFIG
--------------------------------------------------------

  ALTER TABLE "CUE3"."CONFIG" MODIFY ("STR_KEY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."CONFIG" MODIFY ("PK_CONFIG" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."CONFIG" ADD CONSTRAINT "C_SHOW_UK" UNIQUE ("STR_KEY") ENABLE;
  ALTER TABLE "CUE3"."CONFIG" ADD CONSTRAINT "C_PK_PKCONFIG" PRIMARY KEY ("PK_CONFIG") ENABLE;
--------------------------------------------------------
--  Constraints for Table DEED
--------------------------------------------------------

  ALTER TABLE "CUE3"."DEED" ADD CONSTRAINT "C_PK_DEED" PRIMARY KEY ("PK_DEED") ENABLE;
  ALTER TABLE "CUE3"."DEED" MODIFY ("B_BLACKOUT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEED" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEED" MODIFY ("PK_OWNER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEED" MODIFY ("PK_DEED" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table DEPEND
--------------------------------------------------------

  ALTER TABLE "CUE3"."DEPEND" MODIFY ("B_COMPOSITE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("STR_SIGNATURE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("STR_TARGET" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("B_ANY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("B_ACTIVE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("STR_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("PK_JOB_DEPEND_ER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("PK_JOB_DEPEND_ON" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" MODIFY ("PK_DEPEND" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPEND" ADD CONSTRAINT "C_DEPEND_PK" PRIMARY KEY ("PK_DEPEND") ENABLE;
--------------------------------------------------------
--  Constraints for Table DEPT
--------------------------------------------------------

  ALTER TABLE "CUE3"."DEPT" ADD CONSTRAINT "C_DEPT_PK" PRIMARY KEY ("PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."DEPT" MODIFY ("B_DEFAULT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPT" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DEPT" MODIFY ("PK_DEPT" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table DR$I_HOST_STR_TAGS$I
--------------------------------------------------------

  ALTER TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" MODIFY ("DR$TOKEN_INFO" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" MODIFY ("DR$ROWID" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" MODIFY ("DR$TOKEN_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."DR$I_HOST_STR_TAGS$I" MODIFY ("DR$TOKEN" NOT NULL ENABLE);

--------------------------------------------------------
--  Constraints for Table FACILITY
--------------------------------------------------------

  ALTER TABLE "CUE3"."FACILITY" ADD CONSTRAINT "C_FACILITY_PK" PRIMARY KEY ("PK_FACILITY") ENABLE;
  ALTER TABLE "CUE3"."FACILITY" MODIFY ("B_DEFAULT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FACILITY" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FACILITY" MODIFY ("PK_FACILITY" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table FILTER
--------------------------------------------------------

  ALTER TABLE "CUE3"."FILTER" MODIFY ("B_ENABLED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" MODIFY ("F_ORDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" MODIFY ("STR_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" MODIFY ("PK_FILTER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FILTER" ADD CONSTRAINT "C_FILTER_PK" PRIMARY KEY ("PK_FILTER") ENABLE;
--------------------------------------------------------
--  Constraints for Table FOLDER
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER" MODIFY ("F_ORDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("B_EXCLUDE_MANAGED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_JOB_PRIORITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_JOB_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_JOB_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("PK_DEPT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("B_DEFAULT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("INT_PRIORITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" MODIFY ("PK_FOLDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER" ADD CONSTRAINT "C_FOLDER_PK" PRIMARY KEY ("PK_FOLDER") ENABLE;
  ALTER TABLE "CUE3"."FOLDER" ADD CONSTRAINT "C_FOLDER_UK" UNIQUE ("PK_PARENT_FOLDER", "STR_NAME") ENABLE;
--------------------------------------------------------
--  Constraints for Table FOLDER_LEVEL
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER_LEVEL" MODIFY ("INT_LEVEL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_LEVEL" MODIFY ("PK_FOLDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_LEVEL" MODIFY ("PK_FOLDER_LEVEL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_LEVEL" ADD CONSTRAINT "C_FOLDER_LEVEL_UK" UNIQUE ("PK_FOLDER") ENABLE;
  ALTER TABLE "CUE3"."FOLDER_LEVEL" ADD CONSTRAINT "C_FOLDER_LEVEL_PK" PRIMARY KEY ("PK_FOLDER_LEVEL") ENABLE;
--------------------------------------------------------
--  Constraints for Table FOLDER_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER_RESOURCE" ADD CONSTRAINT "C_FOLDER_RESOURCE_PK" PRIMARY KEY ("PK_FOLDER_RESOURCE") ENABLE;
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("FLOAT_TIER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("INT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("PK_FOLDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FOLDER_RESOURCE" MODIFY ("PK_FOLDER_RESOURCE" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table FRAME
--------------------------------------------------------

  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_TOTAL_PAST_CORE_TIME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_GPU_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_CHECKPOINT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("STR_CHECKPOINT_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_LAYER_ORDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_DISPATCH_ORDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_MEM_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_MEM_MAX_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_MEM_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_RETRIES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_EXIT_STATUS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_DEPEND_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("INT_NUMBER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("STR_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" MODIFY ("PK_FRAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME" ADD CONSTRAINT "C_FRAME_STR_NAME_UNQ" UNIQUE ("STR_NAME", "PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."FRAME" ADD CONSTRAINT "C_FRAME_PK" PRIMARY KEY ("PK_FRAME") ENABLE;
--------------------------------------------------------
--  Constraints for Table FRAME_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_CHECKPOINT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" ADD CONSTRAINT "C_FRAME_HISTORY_PK" PRIMARY KEY ("PK_FRAME_HISTORY") ENABLE;
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_TS_STOPPED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_TS_STARTED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_EXIT_STATUS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_MEM_MAX_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("INT_MEM_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("STR_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("PK_FRAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."FRAME_HISTORY" MODIFY ("PK_FRAME_HISTORY" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table HOST
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_GPU_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_GPU" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_THREAD_MODE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("B_COMMENT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("B_REBOOT_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("B_UNLOCK_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("B_UNLOCK_BOOT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_MEM_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_MEM" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_CORES_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_PROCS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("B_NIMBY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("STR_LOCK_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("PK_ALLOC" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST" ADD CONSTRAINT "C_HOST_UK" UNIQUE ("STR_NAME") ENABLE;
  ALTER TABLE "CUE3"."HOST" ADD CONSTRAINT "C_HOST_PK" PRIMARY KEY ("PK_HOST") ENABLE;
  ALTER TABLE "CUE3"."HOST" ADD CONSTRAINT "C_STR_HOST_FQDN_UK" UNIQUE ("STR_FQDN") ENABLE;
--------------------------------------------------------
--  Constraints for Table HOST_LOCAL
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_GPU_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_GPU_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" ADD CONSTRAINT "C_PK_HOST_LOCAL" PRIMARY KEY ("PK_HOST_LOCAL") ENABLE;
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("STR_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("B_ACTIVE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("FLOAT_TIER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_THREADS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_CORES_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_CORES_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_MEM_IDLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("INT_MEM_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_LOCAL" MODIFY ("PK_HOST_LOCAL" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table HOST_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_GPU_FREE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_GPU_TOTAL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("STR_OS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("STR_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("TS_BOOTED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("TS_PING" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_LOAD" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_MCP_FREE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_MCP_TOTAL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_SWAP_FREE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_SWAP_TOTAL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_MEM_FREE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("INT_MEM_TOTAL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" MODIFY ("PK_HOST_STAT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_STAT" ADD CONSTRAINT "C_HOST_STAT_PK_HOST_UK" UNIQUE ("PK_HOST") ENABLE;
  ALTER TABLE "CUE3"."HOST_STAT" ADD CONSTRAINT "C_HOSTSTAT_PK" PRIMARY KEY ("PK_HOST_STAT") ENABLE;
--------------------------------------------------------
--  Constraints for Table HOST_TAG
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST_TAG" MODIFY ("B_CONSTANT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_TAG" MODIFY ("STR_TAG_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_TAG" MODIFY ("STR_TAG" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_TAG" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_TAG" MODIFY ("PK_HOST_TAG" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."HOST_TAG" ADD CONSTRAINT "C_HOST_TAG_PK" PRIMARY KEY ("PK_HOST_TAG") ENABLE;
--------------------------------------------------------
--  Constraints for Table JOB
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB" MODIFY ("PK_FACILITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("B_COMMENT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("B_AUTO_UNBOOK" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("B_AUTO_BOOK" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_MAX_RETRIES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_LAYER_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_FRAME_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("B_AUTOEAT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("B_PAUSED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_UID" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_LOG_DIR" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_STATE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_USER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_SHOT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("PK_FOLDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_UK" UNIQUE ("STR_VISIBLE_NAME") ENABLE;
  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_PK" PRIMARY KEY ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_OS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("TS_UPDATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("STR_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("TS_STARTED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB" MODIFY ("PK_DEPT" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_ENV
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_ENV" ADD CONSTRAINT "C_JOB_ENV_PK" PRIMARY KEY ("PK_JOB_ENV") ENABLE;
  ALTER TABLE "CUE3"."JOB_ENV" MODIFY ("PK_JOB_ENV" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_TS_STARTED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("PK_DEPT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("PK_FACILITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("B_ARCHIVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_RUNNING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_SUCCEEDED_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_EATEN_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_DEPEND_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_DEAD_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_WAITING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_LAYER_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_FRAME_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_CORE_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_CORE_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("STR_USER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("STR_SHOT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_HISTORY" ADD CONSTRAINT "C_JOB_HISTORY_PK" PRIMARY KEY ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."JOB_HISTORY" MODIFY ("INT_TS_STOPPED" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_LOCAL
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_LOCAL" ADD CONSTRAINT "C_PK_JOB_LOCAL" PRIMARY KEY ("PK_JOB_LOCAL") ENABLE;
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("INT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("STR_SOURCE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_LOCAL" MODIFY ("PK_JOB_LOCAL" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_MEM
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_MEM" ADD CONSTRAINT "C_JOB_MEM_PK" PRIMARY KEY ("PK_JOB_MEM") ENABLE;
  ALTER TABLE "CUE3"."JOB_MEM" MODIFY ("INT_MAX_VSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_MEM" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_MEM" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_MEM" MODIFY ("PK_JOB_MEM" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_POST
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_POST" ADD CONSTRAINT "C_JOB_POST_PK" PRIMARY KEY ("PK_JOB_POST") ENABLE;
  ALTER TABLE "CUE3"."JOB_POST" MODIFY ("PK_POST_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_POST" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_POST" MODIFY ("PK_JOB_POST" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table JOB_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_LOCAL_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_PRIORITY" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("FLOAT_TIER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_MAX_VSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" MODIFY ("PK_JOB_RESOURCE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_RESOURCE" ADD CONSTRAINT "C_JOB_RESOURCE_UK" UNIQUE ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."JOB_RESOURCE" ADD CONSTRAINT "C_JOB_RESOURCE_PK" PRIMARY KEY ("PK_JOB_RESOURCE") ENABLE;
--------------------------------------------------------
--  Constraints for Table JOB_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_CHECKPOINT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_SUCCEEDED_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_EATEN_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_DEPEND_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_DEAD_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_RUNNING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("INT_WAITING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" MODIFY ("PK_JOB_STAT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_STAT" ADD CONSTRAINT "C_JOB_STAT_PK" PRIMARY KEY ("PK_JOB_STAT") ENABLE;
--------------------------------------------------------
--  Constraints for Table JOB_USAGE
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_CLOCK_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_CLOCK_TIME_HIGH" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_CLOCK_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_FRAME_FAIL_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_FRAME_SUCCESS_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_CORE_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("INT_CORE_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" MODIFY ("PK_JOB_USAGE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."JOB_USAGE" ADD CONSTRAINT "C_JOB_USAGE_PK_JOB_UNIQ" UNIQUE ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."JOB_USAGE" ADD CONSTRAINT "C_JOB_USAGE_PK" PRIMARY KEY ("PK_JOB_USAGE") ENABLE;
--------------------------------------------------------
--  Constraints for Table LAYER
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_GPU_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" ADD CONSTRAINT "C_LAYER_STR_NAME_UNQ" UNIQUE ("STR_NAME", "PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER" ADD CONSTRAINT "C_LAYER_PK" PRIMARY KEY ("PK_LAYER") ENABLE;
  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_CORES_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("B_OPTIMIZE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_SERVICES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("B_THREADABLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_TAGS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_MEM_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_CORES_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_DISPATCH_ORDER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("INT_CHUNK_SIZE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_RANGE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_CMD" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER" MODIFY ("PK_LAYER" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_ENV
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_ENV" ADD CONSTRAINT "C_LAYER_ENV_PK" PRIMARY KEY ("PK_LAYER_ENV") ENABLE;
  ALTER TABLE "CUE3"."LAYER_ENV" MODIFY ("PK_LAYER_ENV" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_HISTORY" ADD CONSTRAINT "C_LAYER_HISTORY_PK" PRIMARY KEY ("PK_LAYER") ENABLE;
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("B_ARCHIVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_RUNNING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_SUCCEEDED_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_EATEN_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_DEPEND_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_DEAD_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_WAITING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_LAYER_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_FRAME_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_CORE_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_CORE_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_MEM_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("INT_CORES_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("STR_TYPE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_HISTORY" MODIFY ("PK_LAYER" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_MEM
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_MEM" ADD CONSTRAINT "C_LAYER_MEM_PK" PRIMARY KEY ("PK_LAYER_MEM") ENABLE;
  ALTER TABLE "CUE3"."LAYER_MEM" MODIFY ("INT_MAX_VSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_MEM" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_MEM" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_MEM" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_MEM" MODIFY ("PK_LAYER_MEM" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_OUTPUT
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_OUTPUT" ADD CONSTRAINT "C_PK_LAYER_OUTPUT" PRIMARY KEY ("PK_LAYER_OUTPUT") ENABLE;
  ALTER TABLE "CUE3"."LAYER_OUTPUT" MODIFY ("STR_FILESPEC" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_OUTPUT" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_OUTPUT" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_OUTPUT" MODIFY ("PK_LAYER_OUTPUT" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_RESOURCE" ADD CONSTRAINT "C_LAYERRESOURCE_UK" UNIQUE ("PK_LAYER") ENABLE;
  ALTER TABLE "CUE3"."LAYER_RESOURCE" ADD CONSTRAINT "C_LAYERRESOURCE_PK" PRIMARY KEY ("PK_LAYER_RESOURCE") ENABLE;
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("INT_MAX_VSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("INT_MAX_RSS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_RESOURCE" MODIFY ("PK_LAYER_RESOURCE" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_STAT" ADD CONSTRAINT "C_LAYERSTAT_PK" PRIMARY KEY ("PK_LAYER_STAT") ENABLE;
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_CHECKPOINT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_SUCCEEDED_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_EATEN_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_DEPEND_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_DEAD_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_RUNNING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_WAITING_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("INT_TOTAL_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_STAT" MODIFY ("PK_LAYER_STAT" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table LAYER_USAGE
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_USAGE" ADD CONSTRAINT "C_LAYER_USAGE_PK_LAYER_UK" UNIQUE ("PK_LAYER") ENABLE;
  ALTER TABLE "CUE3"."LAYER_USAGE" ADD CONSTRAINT "C_LAYER_USAGE_PK" PRIMARY KEY ("PK_LAYER_USAGE") ENABLE;
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CLOCK_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CLOCK_TIME_LOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CLOCK_TIME_HIGH" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CLOCK_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_FRAME_FAIL_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_FRAME_SUCCESS_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CORE_TIME_FAIL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("INT_CORE_TIME_SUCCESS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("PK_JOB" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("PK_LAYER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."LAYER_USAGE" MODIFY ("PK_LAYER_USAGE" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table MATCHER
--------------------------------------------------------

  ALTER TABLE "CUE3"."MATCHER" ADD CONSTRAINT "C_MATCHER_PK" PRIMARY KEY ("PK_MATCHER") ENABLE;
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("STR_VALUE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("STR_MATCH" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("STR_SUBJECT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("PK_FILTER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."MATCHER" MODIFY ("PK_MATCHER" NOT NULL ENABLE);

--------------------------------------------------------
--  Constraints for Table OWNER
--------------------------------------------------------

  ALTER TABLE "CUE3"."OWNER" ADD CONSTRAINT "C_PK_OWNER" PRIMARY KEY ("PK_OWNER") ENABLE;
  ALTER TABLE "CUE3"."OWNER" MODIFY ("TS_UPDATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."OWNER" MODIFY ("TS_CREATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."OWNER" MODIFY ("STR_USERNAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."OWNER" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."OWNER" MODIFY ("PK_OWNER" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table POINT
--------------------------------------------------------

  ALTER TABLE "CUE3"."POINT" ADD CONSTRAINT "C_POINT_PK_SHOW_DEPT" UNIQUE ("PK_SHOW", "PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."POINT" ADD CONSTRAINT "C_POINT_PK" PRIMARY KEY ("PK_POINT") ENABLE;
  ALTER TABLE "CUE3"."POINT" MODIFY ("TS_UPDATED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("FLOAT_TIER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("B_MANAGED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("PK_DEPT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."POINT" MODIFY ("PK_POINT" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table PROC
--------------------------------------------------------

  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_GPU_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" ADD CONSTRAINT "C_PROC_UK" UNIQUE ("PK_FRAME") ENABLE;
  ALTER TABLE "CUE3"."PROC" ADD CONSTRAINT "C_PROC_PK" PRIMARY KEY ("PK_PROC") ENABLE;
  ALTER TABLE "CUE3"."PROC" MODIFY ("TS_DISPATCHED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("TS_BOOKED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("TS_PING" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("B_LOCAL" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_VIRT_MAX_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_VIRT_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_MEM_PRE_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("B_UNBOOKED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_MEM_MAX_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_MEM_USED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_MEM_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("INT_CORES_RESERVED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("PK_HOST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."PROC" MODIFY ("PK_PROC" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table SERVICE
--------------------------------------------------------

  ALTER TABLE "CUE3"."SERVICE" MODIFY ("INT_GPU_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" ADD CONSTRAINT "C_PK_SERVICE" PRIMARY KEY ("PK_SERVICE") ENABLE;
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("INT_CORES_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("STR_TAGS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("INT_MEM_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("INT_CORES_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("B_THREADABLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SERVICE" MODIFY ("PK_SERVICE" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table SHOW
--------------------------------------------------------

  ALTER TABLE "CUE3"."SHOW" MODIFY ("B_ACTIVE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("B_DISPATCH_ENABLED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("B_BOOKING_ENABLED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_FRAME_FAIL_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_FRAME_SUCCESS_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_JOB_INSERT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_FRAME_INSERT_COUNT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_DEFAULT_MAX_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("INT_DEFAULT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" ADD CONSTRAINT "C_SHOW_PK" PRIMARY KEY ("PK_SHOW") ENABLE;
  ALTER TABLE "CUE3"."SHOW" MODIFY ("B_PAUSED" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW" MODIFY ("PK_SHOW" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table SHOW_ALIAS
--------------------------------------------------------

  ALTER TABLE "CUE3"."SHOW_ALIAS" ADD CONSTRAINT "C_SHOW_ALIAS_PK" PRIMARY KEY ("PK_SHOW_ALIAS") ENABLE;
  ALTER TABLE "CUE3"."SHOW_ALIAS" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_ALIAS" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_ALIAS" MODIFY ("PK_SHOW_ALIAS" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table SHOW_SERVICE
--------------------------------------------------------

  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("INT_GPU_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" ADD CONSTRAINT "C_PK_SHOW_SERVICE" PRIMARY KEY ("PK_SHOW_SERVICE") ENABLE;
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("INT_CORES_MAX" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("STR_TAGS" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("INT_MEM_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("INT_CORES_MIN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("B_THREADABLE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SHOW_SERVICE" MODIFY ("PK_SHOW_SERVICE" NOT NULL ENABLE);

  GRANT UPDATE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT DELETE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT INSERT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT SELECT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;

--------------------------------------------------------
--  Constraints for Table SUBSCRIPTION
--------------------------------------------------------

  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("FLOAT_TIER" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("INT_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("INT_BURST" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("INT_SIZE" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("PK_SHOW" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("PK_ALLOC" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" MODIFY ("PK_SUBSCRIPTION" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."SUBSCRIPTION" ADD CONSTRAINT "C_SUBSCRIPTION_UK" UNIQUE ("PK_SHOW", "PK_ALLOC") ENABLE;
  ALTER TABLE "CUE3"."SUBSCRIPTION" ADD CONSTRAINT "C_SUBSCRIPTION_PK" PRIMARY KEY ("PK_SUBSCRIPTION") ENABLE;
--------------------------------------------------------
--  Constraints for Table TASK
--------------------------------------------------------

  ALTER TABLE "CUE3"."TASK" ADD CONSTRAINT "C_TASK_UNIQ" UNIQUE ("STR_SHOT", "PK_POINT") ENABLE;
  ALTER TABLE "CUE3"."TASK" ADD CONSTRAINT "C_TASK_PK" PRIMARY KEY ("PK_TASK") ENABLE;
  ALTER TABLE "CUE3"."TASK" MODIFY ("INT_ADJUST_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK" MODIFY ("INT_MIN_CORES" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK" MODIFY ("STR_SHOT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK" MODIFY ("PK_POINT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK" MODIFY ("PK_TASK" NOT NULL ENABLE);
--------------------------------------------------------
--  Constraints for Table TASK_LOCK
--------------------------------------------------------

  ALTER TABLE "CUE3"."TASK_LOCK" MODIFY ("TS_LASTRUN" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK_LOCK" MODIFY ("INT_TIMEOUT" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK_LOCK" MODIFY ("INT_LOCK" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK_LOCK" MODIFY ("STR_NAME" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK_LOCK" MODIFY ("PK_TASK_LOCK" NOT NULL ENABLE);
  ALTER TABLE "CUE3"."TASK_LOCK" ADD CONSTRAINT "C_TASK_LOCK_PK" PRIMARY KEY ("PK_TASK_LOCK") ENABLE;



--------------------------------------------------------
--  DDL for Index C_ACTION_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_ACTION_PK" ON "CUE3"."ACTION" ("PK_ACTION") 
  ;
--------------------------------------------------------
--  DDL for Index C_ALLOC_NAME_UNIQ
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_ALLOC_NAME_UNIQ" ON "CUE3"."ALLOC" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_ALLOC_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_ALLOC_PK" ON "CUE3"."ALLOC" ("PK_ALLOC") 
  ;
--------------------------------------------------------
--  DDL for Index C_COMMENT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_COMMENT_PK" ON "CUE3"."COMMENTS" ("PK_COMMENT") 
  ;
--------------------------------------------------------
--  DDL for Index C_DEPEND_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_DEPEND_PK" ON "CUE3"."DEPEND" ("PK_DEPEND") 
  ;
--------------------------------------------------------
--  DDL for Index C_DEPT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_DEPT_PK" ON "CUE3"."DEPT" ("PK_DEPT") 
  ;
--------------------------------------------------------
--  DDL for Index C_FACILITY_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FACILITY_PK" ON "CUE3"."FACILITY" ("PK_FACILITY") 
  ;
--------------------------------------------------------
--  DDL for Index C_FILTER_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FILTER_PK" ON "CUE3"."FILTER" ("PK_FILTER") 
  ;
--------------------------------------------------------
--  DDL for Index C_FOLDER_LEVEL_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FOLDER_LEVEL_PK" ON "CUE3"."FOLDER_LEVEL" ("PK_FOLDER_LEVEL") 
  ;
--------------------------------------------------------
--  DDL for Index C_FOLDER_LEVEL_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FOLDER_LEVEL_UK" ON "CUE3"."FOLDER_LEVEL" ("PK_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index C_FOLDER_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FOLDER_PK" ON "CUE3"."FOLDER" ("PK_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index C_FOLDER_RESOURCE_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FOLDER_RESOURCE_PK" ON "CUE3"."FOLDER_RESOURCE" ("PK_FOLDER_RESOURCE") 
  ;
--------------------------------------------------------
--  DDL for Index C_FOLDER_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FOLDER_UK" ON "CUE3"."FOLDER" ("PK_PARENT_FOLDER", "STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_FRAME_HISTORY_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FRAME_HISTORY_PK" ON "CUE3"."FRAME_HISTORY" ("PK_FRAME_HISTORY") 
  ;
--------------------------------------------------------
--  DDL for Index C_FRAME_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FRAME_PK" ON "CUE3"."FRAME" ("PK_FRAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_FRAME_STR_NAME_UNQ
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_FRAME_STR_NAME_UNQ" ON "CUE3"."FRAME" ("STR_NAME", "PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_HOSTSTAT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_HOSTSTAT_PK" ON "CUE3"."HOST_STAT" ("PK_HOST_STAT") 
  ;
--------------------------------------------------------
--  DDL for Index C_HOST_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_HOST_PK" ON "CUE3"."HOST" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index C_HOST_STAT_PK_HOST_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_HOST_STAT_PK_HOST_UK" ON "CUE3"."HOST_STAT" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index C_HOST_TAG_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_HOST_TAG_PK" ON "CUE3"."HOST_TAG" ("PK_HOST_TAG") 
  ;
--------------------------------------------------------
--  DDL for Index C_HOST_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_HOST_UK" ON "CUE3"."HOST" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_ENV_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_ENV_PK" ON "CUE3"."JOB_ENV" ("PK_JOB_ENV") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_HISTORY_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_HISTORY_PK" ON "CUE3"."JOB_HISTORY" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_MEM_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_MEM_PK" ON "CUE3"."JOB_MEM" ("PK_JOB_MEM") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_PK" ON "CUE3"."JOB" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_POST_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_POST_PK" ON "CUE3"."JOB_POST" ("PK_JOB_POST") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_RESOURCE_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_RESOURCE_PK" ON "CUE3"."JOB_RESOURCE" ("PK_JOB_RESOURCE") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_RESOURCE_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_RESOURCE_UK" ON "CUE3"."JOB_RESOURCE" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_STAT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_STAT_PK" ON "CUE3"."JOB_STAT" ("PK_JOB_STAT") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_UK" ON "CUE3"."JOB" ("STR_VISIBLE_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_USAGE_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_USAGE_PK" ON "CUE3"."JOB_USAGE" ("PK_JOB_USAGE") 
  ;
--------------------------------------------------------
--  DDL for Index C_JOB_USAGE_PK_JOB_UNIQ
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_JOB_USAGE_PK_JOB_UNIQ" ON "CUE3"."JOB_USAGE" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYERRESOURCE_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYERRESOURCE_PK" ON "CUE3"."LAYER_RESOURCE" ("PK_LAYER_RESOURCE") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYERRESOURCE_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYERRESOURCE_UK" ON "CUE3"."LAYER_RESOURCE" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYERSTAT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYERSTAT_PK" ON "CUE3"."LAYER_STAT" ("PK_LAYER_STAT") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_ENV_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_ENV_PK" ON "CUE3"."LAYER_ENV" ("PK_LAYER_ENV") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_HISTORY_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_HISTORY_PK" ON "CUE3"."LAYER_HISTORY" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_MEM_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_MEM_PK" ON "CUE3"."LAYER_MEM" ("PK_LAYER_MEM") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_PK" ON "CUE3"."LAYER" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_STR_NAME_UNQ
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_STR_NAME_UNQ" ON "CUE3"."LAYER" ("STR_NAME", "PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_USAGE_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_USAGE_PK" ON "CUE3"."LAYER_USAGE" ("PK_LAYER_USAGE") 
  ;
--------------------------------------------------------
--  DDL for Index C_LAYER_USAGE_PK_LAYER_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_LAYER_USAGE_PK_LAYER_UK" ON "CUE3"."LAYER_USAGE" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index C_MATCHER_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_MATCHER_PK" ON "CUE3"."MATCHER" ("PK_MATCHER") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_DEED
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_DEED" ON "CUE3"."DEED" ("PK_DEED") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_HOST_LOCAL
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_HOST_LOCAL" ON "CUE3"."HOST_LOCAL" ("PK_HOST_LOCAL") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_JOB_LOCAL
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_JOB_LOCAL" ON "CUE3"."JOB_LOCAL" ("PK_JOB_LOCAL") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_LAYER_OUTPUT
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_LAYER_OUTPUT" ON "CUE3"."LAYER_OUTPUT" ("PK_LAYER_OUTPUT") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_OWNER
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_OWNER" ON "CUE3"."OWNER" ("PK_OWNER") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_PKCONFIG
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_PKCONFIG" ON "CUE3"."CONFIG" ("PK_CONFIG") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_SERVICE
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_SERVICE" ON "CUE3"."SERVICE" ("PK_SERVICE") 
  ;
--------------------------------------------------------
--  DDL for Index C_PK_SHOW_SERVICE
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PK_SHOW_SERVICE" ON "CUE3"."SHOW_SERVICE" ("PK_SHOW_SERVICE") 
  ;
--------------------------------------------------------
--  DDL for Index C_POINT_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_POINT_PK" ON "CUE3"."POINT" ("PK_POINT") 
  ;
--------------------------------------------------------
--  DDL for Index C_POINT_PK_SHOW_DEPT
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_POINT_PK_SHOW_DEPT" ON "CUE3"."POINT" ("PK_SHOW", "PK_DEPT") 
  ;
--------------------------------------------------------
--  DDL for Index C_PROC_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PROC_PK" ON "CUE3"."PROC" ("PK_PROC") 
  ;
--------------------------------------------------------
--  DDL for Index C_PROC_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_PROC_UK" ON "CUE3"."PROC" ("PK_FRAME") 
  ;
--------------------------------------------------------
--  DDL for Index C_SHOW_ALIAS_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_SHOW_ALIAS_PK" ON "CUE3"."SHOW_ALIAS" ("PK_SHOW_ALIAS") 
  ;
--------------------------------------------------------
--  DDL for Index C_SHOW_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_SHOW_PK" ON "CUE3"."SHOW" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index C_SHOW_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_SHOW_UK" ON "CUE3"."CONFIG" ("STR_KEY") 
  ;
--------------------------------------------------------
--  DDL for Index C_STR_HOST_FQDN_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_STR_HOST_FQDN_UK" ON "CUE3"."HOST" ("STR_FQDN") 
  ;
--------------------------------------------------------
--  DDL for Index C_SUBSCRIPTION_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_SUBSCRIPTION_PK" ON "CUE3"."SUBSCRIPTION" ("PK_SUBSCRIPTION") 
  ;
--------------------------------------------------------
--  DDL for Index C_SUBSCRIPTION_UK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_SUBSCRIPTION_UK" ON "CUE3"."SUBSCRIPTION" ("PK_SHOW", "PK_ALLOC") 
  ;
--------------------------------------------------------
--  DDL for Index C_TASK_LOCK_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_TASK_LOCK_PK" ON "CUE3"."TASK_LOCK" ("PK_TASK_LOCK") 
  ;
--------------------------------------------------------
--  DDL for Index C_TASK_PK
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_TASK_PK" ON "CUE3"."TASK" ("PK_TASK") 
  ;
--------------------------------------------------------
--  DDL for Index C_TASK_UNIQ
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."C_TASK_UNIQ" ON "CUE3"."TASK" ("STR_SHOT", "PK_POINT") 
  ;
--------------------------------------------------------
--  DDL for Index DR$I_HOST_STR_TAGS$R
--------------------------------------------------------

  CREATE INDEX "CUE3"."DR$I_HOST_STR_TAGS$R" ON "CUE3"."DR$I_HOST_STR_TAGS$I" ("DR$ROWID") 
  ;
--------------------------------------------------------
--  DDL for Index DR$I_HOST_STR_TAGS$X
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."DR$I_HOST_STR_TAGS$X" ON "CUE3"."DR$I_HOST_STR_TAGS$I" ("DR$TOKEN", "DR$TOKEN_TYPE", "DR$ROWID") 
  ;
--------------------------------------------------------
--  DDL for Index DR$I_HOST_STR_TAGS01
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."DR$I_HOST_STR_TAGS01" ON "CUE3"."DR$I_HOST_STR_TAGS$I" ("DR$TOKEN", "DR$TOKEN_TYPE", "STR_NAME", "DR$ROWID") 
  ;
--------------------------------------------------------
--  DDL for Index I_ACTION_PK_FILTER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_ACTION_PK_FILTER" ON "CUE3"."ACTION" ("PK_FILTER") 
  ;
--------------------------------------------------------
--  DDL for Index I_ACTION_PK_GROUP
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_ACTION_PK_GROUP" ON "CUE3"."ACTION" ("PK_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_ALLOC_PK_FACILITY
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_ALLOC_PK_FACILITY" ON "CUE3"."ALLOC" ("PK_FACILITY") 
  ;
--------------------------------------------------------
--  DDL for Index I_BOOKING_3
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_BOOKING_3" ON "CUE3"."JOB" ("STR_STATE", "B_PAUSED", "PK_SHOW", "PK_FACILITY") 
  ;
--------------------------------------------------------
--  DDL for Index I_COMMENT_PK_HOST
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_COMMENT_PK_HOST" ON "CUE3"."COMMENTS" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_COMMENT_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_COMMENT_PK_JOB" ON "CUE3"."COMMENTS" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEED_PK_HOST
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_DEED_PK_HOST" ON "CUE3"."DEED" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEED_PK_OWNER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEED_PK_OWNER" ON "CUE3"."DEED" ("PK_OWNER") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_B_COMPOSITE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_B_COMPOSITE" ON "CUE3"."DEPEND" ("B_COMPOSITE") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_ER_FRAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_ER_FRAME" ON "CUE3"."DEPEND" ("PK_FRAME_DEPEND_ER") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_ER_LAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_ER_LAYER" ON "CUE3"."DEPEND" ("PK_LAYER_DEPEND_ER") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_ON_FRAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_ON_FRAME" ON "CUE3"."DEPEND" ("PK_FRAME_DEPEND_ON") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_ON_LAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_ON_LAYER" ON "CUE3"."DEPEND" ("PK_LAYER_DEPEND_ON") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_PKPARENT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_PKPARENT" ON "CUE3"."DEPEND" ("PK_PARENT") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_PK_ER_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_PK_ER_JOB" ON "CUE3"."DEPEND" ("PK_JOB_DEPEND_ER") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_PK_ON_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_PK_ON_JOB" ON "CUE3"."DEPEND" ("PK_JOB_DEPEND_ON") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_SIGNATURE
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_DEPEND_SIGNATURE" ON "CUE3"."DEPEND" ("STR_SIGNATURE") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_STR_TARGET
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_STR_TARGET" ON "CUE3"."DEPEND" ("STR_TARGET") 
  ;
--------------------------------------------------------
--  DDL for Index I_DEPEND_STR_TYPE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_DEPEND_STR_TYPE" ON "CUE3"."DEPEND" ("STR_TYPE") 
  ;
--------------------------------------------------------
--  DDL for Index I_FILTERS_PK_SHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FILTERS_PK_SHOW" ON "CUE3"."FILTER" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDERRESOURCE_PKFOLDER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDERRESOURCE_PKFOLDER" ON "CUE3"."FOLDER_RESOURCE" ("PK_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDER_PKPARENTFOLDER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDER_PKPARENTFOLDER" ON "CUE3"."FOLDER" ("PK_PARENT_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDER_PKSHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDER_PKSHOW" ON "CUE3"."FOLDER" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDER_RESOURCE_FL_TIER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDER_RESOURCE_FL_TIER" ON "CUE3"."FOLDER_RESOURCE" ("FLOAT_TIER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDER_RES_INT_MAX_CORES
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDER_RES_INT_MAX_CORES" ON "CUE3"."FOLDER_RESOURCE" ("INT_MAX_CORES") 
  ;
--------------------------------------------------------
--  DDL for Index I_FOLDER_STRNAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FOLDER_STRNAME" ON "CUE3"."FOLDER" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_DISPATCH_IDX
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_DISPATCH_IDX" ON "CUE3"."FRAME" ("INT_DISPATCH_ORDER", "INT_LAYER_ORDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_INT_EXIT_STAT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_INT_EXIT_STAT" ON "CUE3"."FRAME_HISTORY" ("INT_EXIT_STATUS") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_INT_TS_STOPPED
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_INT_TS_STOPPED" ON "CUE3"."FRAME_HISTORY" ("INT_TS_STOPPED") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_PK_ALLOC
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_PK_ALLOC" ON "CUE3"."FRAME_HISTORY" ("PK_ALLOC") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_PK_FRAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_PK_FRAME" ON "CUE3"."FRAME_HISTORY" ("PK_FRAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_PK_JOB" ON "CUE3"."FRAME_HISTORY" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_PK_LAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_PK_LAYER" ON "CUE3"."FRAME_HISTORY" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_STR_STATE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_STR_STATE" ON "CUE3"."FRAME_HISTORY" ("STR_STATE") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_HISTORY_TS_START_STOP
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_HISTORY_TS_START_STOP" ON "CUE3"."FRAME_HISTORY" ("INT_TS_STARTED", "INT_TS_STOPPED") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_INT_GPU_RESERVED
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_INT_GPU_RESERVED" ON "CUE3"."FRAME" ("INT_GPU_RESERVED") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_PKJOBLAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_PKJOBLAYER" ON "CUE3"."FRAME" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_PK_JOB" ON "CUE3"."FRAME" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_FRAME_STATE_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_FRAME_STATE_JOB" ON "CUE3"."FRAME" ("STR_STATE", "PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_INT_GPU
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_INT_GPU" ON "CUE3"."HOST" ("INT_GPU") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_INT_GPU_IDLE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_INT_GPU_IDLE" ON "CUE3"."HOST" ("INT_GPU_IDLE") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_LOCAL
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_LOCAL" ON "CUE3"."HOST_LOCAL" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_LOCAL_INT_GPU_IDLE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_LOCAL_INT_GPU_IDLE" ON "CUE3"."HOST_LOCAL" ("INT_GPU_IDLE") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_LOCAL_INT_GPU_MAX
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_LOCAL_INT_GPU_MAX" ON "CUE3"."HOST_LOCAL" ("INT_GPU_MAX") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_LOCAL_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_LOCAL_PK_JOB" ON "CUE3"."HOST_LOCAL" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_LOCAL_UNIQUE
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_HOST_LOCAL_UNIQUE" ON "CUE3"."HOST_LOCAL" ("PK_HOST", "PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_PKALLOC
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_PKALLOC" ON "CUE3"."HOST" ("PK_ALLOC") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_STAT_INT_GPU_FREE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STAT_INT_GPU_FREE" ON "CUE3"."HOST_STAT" ("INT_GPU_FREE") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_STAT_INT_GPU_TOTAL
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STAT_INT_GPU_TOTAL" ON "CUE3"."HOST_STAT" ("INT_GPU_TOTAL") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_STAT_STR_OS
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STAT_STR_OS" ON "CUE3"."HOST_STAT" ("STR_OS") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_STRLOCKSTATE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STRLOCKSTATE" ON "CUE3"."HOST" ("STR_LOCK_STATE") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_STR_TAGS
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STR_TAGS" ON "CUE3"."HOST" ("STR_TAGS") 
   INDEXTYPE IS "CTXSYS"."CTXCAT"  PARAMETERS ('INDEX SET tag_set');
--------------------------------------------------------
--  DDL for Index I_HOST_STR_TAG_TYPE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_STR_TAG_TYPE" ON "CUE3"."HOST_TAG" ("STR_TAG_TYPE") 
  ;
--------------------------------------------------------
--  DDL for Index I_HOST_TAG_PK_HOST
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_HOST_TAG_PK_HOST" ON "CUE3"."HOST_TAG" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_ENV_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_ENV_PK_JOB" ON "CUE3"."JOB_ENV" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_B_ARCHIVED
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_B_ARCHIVED" ON "CUE3"."JOB_HISTORY" ("B_ARCHIVED") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_PK_DEPT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_PK_DEPT" ON "CUE3"."JOB_HISTORY" ("PK_DEPT") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_PK_FACILITY
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_PK_FACILITY" ON "CUE3"."JOB_HISTORY" ("PK_FACILITY") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_PK_SHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_PK_SHOW" ON "CUE3"."JOB_HISTORY" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_STR_NAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_STR_NAME" ON "CUE3"."JOB_HISTORY" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_STR_SHOT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_STR_SHOT" ON "CUE3"."JOB_HISTORY" ("STR_SHOT") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_STR_USER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_STR_USER" ON "CUE3"."JOB_HISTORY" ("STR_USER") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_HISTORY_TS_START_STOP
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_HISTORY_TS_START_STOP" ON "CUE3"."JOB_HISTORY" ("INT_TS_STARTED", "INT_TS_STOPPED") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_LOCAL_PK_HOST
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_JOB_LOCAL_PK_HOST" ON "CUE3"."JOB_LOCAL" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_LOCAL_PK_JOB
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_JOB_LOCAL_PK_JOB" ON "CUE3"."JOB_LOCAL" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_MEM_INT_MAX_RSS
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_MEM_INT_MAX_RSS" ON "CUE3"."JOB_MEM" ("INT_MAX_RSS") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_MEM_PK_JOB
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_JOB_MEM_PK_JOB" ON "CUE3"."JOB_MEM" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_PKGROUP
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_PKGROUP" ON "CUE3"."JOB" ("PK_FOLDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_PKSHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_PKSHOW" ON "CUE3"."JOB" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_PK_DEPT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_PK_DEPT" ON "CUE3"."JOB" ("PK_DEPT") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_PK_FACILITY
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_PK_FACILITY" ON "CUE3"."JOB" ("PK_FACILITY") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_POST_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_POST_PK_JOB" ON "CUE3"."JOB_POST" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_POST_PK_POST_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_POST_PK_POST_JOB" ON "CUE3"."JOB_POST" ("PK_POST_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_RESOURCE_CORES
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_RESOURCE_CORES" ON "CUE3"."JOB_RESOURCE" ("INT_CORES") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_RESOURCE_MAX_C
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_RESOURCE_MAX_C" ON "CUE3"."JOB_RESOURCE" ("INT_MAX_CORES") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_RESOURCE_MIN_MAX
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_RESOURCE_MIN_MAX" ON "CUE3"."JOB_RESOURCE" ("INT_MIN_CORES", "INT_MAX_CORES") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STAT_INT_WAITING_COUNT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_STAT_INT_WAITING_COUNT" ON "CUE3"."JOB_STAT" ("INT_WAITING_COUNT") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STAT_PK_JOB
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_JOB_STAT_PK_JOB" ON "CUE3"."JOB_STAT" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STR_NAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_STR_NAME" ON "CUE3"."JOB" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STR_OS
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_STR_OS" ON "CUE3"."JOB" ("STR_OS") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STR_SHOT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_STR_SHOT" ON "CUE3"."JOB" ("STR_SHOT") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_STR_STATE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_STR_STATE" ON "CUE3"."JOB" ("STR_STATE") 
  ;
--------------------------------------------------------
--  DDL for Index I_JOB_TIER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_JOB_TIER" ON "CUE3"."JOB_RESOURCE" ("FLOAT_TIER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYERSTAT_INT_WAITING_COUNT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYERSTAT_INT_WAITING_COUNT" ON "CUE3"."LAYER_STAT" ("INT_WAITING_COUNT") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYERSTAT_PKJOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYERSTAT_PKJOB" ON "CUE3"."LAYER_STAT" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_B_THREADABLE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_B_THREADABLE" ON "CUE3"."LAYER" ("B_THREADABLE") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_CORES_MEM
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_CORES_MEM" ON "CUE3"."LAYER" ("INT_CORES_MIN", "INT_MEM_MIN") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_CORES_MEM_THREAD
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_CORES_MEM_THREAD" ON "CUE3"."LAYER" ("INT_CORES_MIN", "INT_MEM_MIN", "B_THREADABLE") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_ENV_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_ENV_PK_JOB" ON "CUE3"."LAYER_ENV" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_ENV_PK_LAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_ENV_PK_LAYER" ON "CUE3"."LAYER_ENV" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_HISTORY_B_ARCHIVED
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_HISTORY_B_ARCHIVED" ON "CUE3"."LAYER_HISTORY" ("B_ARCHIVED") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_HISTORY_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_HISTORY_PK_JOB" ON "CUE3"."LAYER_HISTORY" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_HISTORY_STR_NAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_HISTORY_STR_NAME" ON "CUE3"."LAYER_HISTORY" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_HISTORY_STR_TYPE
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_HISTORY_STR_TYPE" ON "CUE3"."LAYER_HISTORY" ("STR_TYPE") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_INT_DISPATCH_ORDER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_INT_DISPATCH_ORDER" ON "CUE3"."LAYER" ("INT_DISPATCH_ORDER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_INT_GPU_MIN
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_INT_GPU_MIN" ON "CUE3"."LAYER" ("INT_GPU_MIN") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_MEM_INT_MAX_RSS
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_MEM_INT_MAX_RSS" ON "CUE3"."LAYER_MEM" ("INT_MAX_RSS") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_MEM_MIN
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_MEM_MIN" ON "CUE3"."LAYER" ("INT_MEM_MIN") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_MEM_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_MEM_PK_JOB" ON "CUE3"."LAYER_MEM" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_MEM_PK_LAYER
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_LAYER_MEM_PK_LAYER" ON "CUE3"."LAYER_MEM" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_OUTPUT_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_OUTPUT_PK_JOB" ON "CUE3"."LAYER_OUTPUT" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_OUTPUT_PK_LAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_OUTPUT_PK_LAYER" ON "CUE3"."LAYER_OUTPUT" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_OUTPUT_UNIQUE
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_LAYER_OUTPUT_UNIQUE" ON "CUE3"."LAYER_OUTPUT" ("PK_LAYER", "STR_FILESPEC") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_PKJOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_PKJOB" ON "CUE3"."LAYER" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_RESOURCE_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_RESOURCE_PK_JOB" ON "CUE3"."LAYER_RESOURCE" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_STAT_PK_LAYER
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_LAYER_STAT_PK_LAYER" ON "CUE3"."LAYER_STAT" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_STRNAME
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_STRNAME" ON "CUE3"."LAYER" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_LAYER_USAGE_PK_JOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_LAYER_USAGE_PK_JOB" ON "CUE3"."LAYER_USAGE" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_MATCHER_PK_FILTER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_MATCHER_PK_FILTER" ON "CUE3"."MATCHER" ("PK_FILTER") 
  ;
--------------------------------------------------------
--  DDL for Index I_OWNER_PK_SHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_OWNER_PK_SHOW" ON "CUE3"."OWNER" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_OWNER_STR_USERNAME
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_OWNER_STR_USERNAME" ON "CUE3"."OWNER" ("STR_USERNAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_POINT_PK_DEPT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_POINT_PK_DEPT" ON "CUE3"."POINT" ("PK_DEPT") 
  ;
--------------------------------------------------------
--  DDL for Index I_POINT_PK_SHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_POINT_PK_SHOW" ON "CUE3"."POINT" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_POINT_TIER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_POINT_TIER" ON "CUE3"."POINT" ("FLOAT_TIER") 
  ;
--------------------------------------------------------
--  DDL for Index I_PROC_INT_GPU_RESERVED
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_PROC_INT_GPU_RESERVED" ON "CUE3"."PROC" ("INT_GPU_RESERVED") 
  ;
--------------------------------------------------------
--  DDL for Index I_PROC_PKHOST
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_PROC_PKHOST" ON "CUE3"."PROC" ("PK_HOST") 
  ;
--------------------------------------------------------
--  DDL for Index I_PROC_PKJOB
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_PROC_PKJOB" ON "CUE3"."PROC" ("PK_JOB") 
  ;
--------------------------------------------------------
--  DDL for Index I_PROC_PKLAYER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_PROC_PKLAYER" ON "CUE3"."PROC" ("PK_LAYER") 
  ;
--------------------------------------------------------
--  DDL for Index I_PROC_PKSHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_PROC_PKSHOW" ON "CUE3"."PROC" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_SERVICE_INT_GPU_MIN
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_SERVICE_INT_GPU_MIN" ON "CUE3"."SERVICE" ("INT_GPU_MIN") 
  ;
--------------------------------------------------------
--  DDL for Index I_SERVICE_STR_NAME
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_SERVICE_STR_NAME" ON "CUE3"."SERVICE" ("STR_NAME") 
  ;
--------------------------------------------------------
--  DDL for Index I_SHOW_ALIAS_PK_SHOW
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_SHOW_ALIAS_PK_SHOW" ON "CUE3"."SHOW_ALIAS" ("PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_SHOW_SERVICE_INT_GPU_MIN
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_SHOW_SERVICE_INT_GPU_MIN" ON "CUE3"."SHOW_SERVICE" ("INT_GPU_MIN") 
  ;
--------------------------------------------------------
--  DDL for Index I_SHOW_SERVICE_STR_NAME
--------------------------------------------------------

  CREATE UNIQUE INDEX "CUE3"."I_SHOW_SERVICE_STR_NAME" ON "CUE3"."SHOW_SERVICE" ("STR_NAME", "PK_SHOW") 
  ;
--------------------------------------------------------
--  DDL for Index I_SUBSCRIPTION_PKALLOC
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_SUBSCRIPTION_PKALLOC" ON "CUE3"."SUBSCRIPTION" ("PK_ALLOC") 
  ;
--------------------------------------------------------
--  DDL for Index I_SUB_TIER
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_SUB_TIER" ON "CUE3"."SUBSCRIPTION" ("FLOAT_TIER") 
  ;
--------------------------------------------------------
--  DDL for Index I_TASK_PK_POINT
--------------------------------------------------------

  CREATE INDEX "CUE3"."I_TASK_PK_POINT" ON "CUE3"."TASK" ("PK_POINT") 
  ;
--------------------------------------------------------
--  DDL for Index MATTHEW_STATS_TAB
--------------------------------------------------------

  CREATE INDEX "CUE3"."MATTHEW_STATS_TAB" ON "CUE3"."MATTHEW_STATS_TAB" ("STATID", "TYPE", "C5", "C1", "C2", "C3", "C4", "VERSION") 
  ;
--------------------------------------------------------
--  Ref Constraints for Table ACTION
--------------------------------------------------------

  ALTER TABLE "CUE3"."ACTION" ADD CONSTRAINT "C_ACTION_PK_FILTER" FOREIGN KEY ("PK_FILTER")
	  REFERENCES "CUE3"."FILTER" ("PK_FILTER") ENABLE;
  ALTER TABLE "CUE3"."ACTION" ADD CONSTRAINT "C_ACTION_PK_FOLDER" FOREIGN KEY ("PK_FOLDER")
	  REFERENCES "CUE3"."FOLDER" ("PK_FOLDER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table ALLOC
--------------------------------------------------------

  ALTER TABLE "CUE3"."ALLOC" ADD CONSTRAINT "C_ALLOC_PK_FACILITY" FOREIGN KEY ("PK_FACILITY")
	  REFERENCES "CUE3"."FACILITY" ("PK_FACILITY") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table COMMENTS
--------------------------------------------------------

  ALTER TABLE "CUE3"."COMMENTS" ADD CONSTRAINT "C_COMMENT_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;
  ALTER TABLE "CUE3"."COMMENTS" ADD CONSTRAINT "C_COMMENT_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;

--------------------------------------------------------
--  Ref Constraints for Table DEED
--------------------------------------------------------

  ALTER TABLE "CUE3"."DEED" ADD CONSTRAINT "C_DEED_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;





--------------------------------------------------------
--  Ref Constraints for Table FILTER
--------------------------------------------------------

  ALTER TABLE "CUE3"."FILTER" ADD CONSTRAINT "C_FILTER_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table FOLDER
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER" ADD CONSTRAINT "C_FOLDER_PK_DEPT" FOREIGN KEY ("PK_DEPT")
	  REFERENCES "CUE3"."DEPT" ("PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."FOLDER" ADD CONSTRAINT "C_FOLDER_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table FOLDER_LEVEL
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER_LEVEL" ADD CONSTRAINT "C_FOLDER_LEVEL_PK_FOLDER" FOREIGN KEY ("PK_FOLDER")
	  REFERENCES "CUE3"."FOLDER" ("PK_FOLDER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table FOLDER_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."FOLDER_RESOURCE" ADD CONSTRAINT "C_FOLDER_RESOURCE_PK_FOLDER" FOREIGN KEY ("PK_FOLDER")
	  REFERENCES "CUE3"."FOLDER" ("PK_FOLDER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table FRAME
--------------------------------------------------------

  ALTER TABLE "CUE3"."FRAME" ADD CONSTRAINT "C_FRAME_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."FRAME" ADD CONSTRAINT "C_FRAME_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table FRAME_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."FRAME_HISTORY" ADD CONSTRAINT "C_FRAME_HISTORY_PK_ALLOC" FOREIGN KEY ("PK_ALLOC")
	  REFERENCES "CUE3"."ALLOC" ("PK_ALLOC") ENABLE;
  ALTER TABLE "CUE3"."FRAME_HISTORY" ADD CONSTRAINT "C_FRAME_HISTORY_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB_HISTORY" ("PK_JOB") ON DELETE CASCADE ENABLE;
  ALTER TABLE "CUE3"."FRAME_HISTORY" ADD CONSTRAINT "C_FRAME_HISTORY_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER_HISTORY" ("PK_LAYER") ON DELETE CASCADE ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table HOST
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST" ADD CONSTRAINT "C_HOST_PK_ALLOC" FOREIGN KEY ("PK_ALLOC")
	  REFERENCES "CUE3"."ALLOC" ("PK_ALLOC") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table HOST_LOCAL
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST_LOCAL" ADD CONSTRAINT "C_HOST_LOCAL_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;
  ALTER TABLE "CUE3"."HOST_LOCAL" ADD CONSTRAINT "C_HOST_LOCAL_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table HOST_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."HOST_STAT" ADD CONSTRAINT "C_HOST_STAT_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;

--------------------------------------------------------
--  Ref Constraints for Table JOB
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_PK_DEPT" FOREIGN KEY ("PK_DEPT")
	  REFERENCES "CUE3"."DEPT" ("PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_PK_FACILITY" FOREIGN KEY ("PK_FACILITY")
	  REFERENCES "CUE3"."FACILITY" ("PK_FACILITY") ENABLE;
  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_PK_FOLDER" FOREIGN KEY ("PK_FOLDER")
	  REFERENCES "CUE3"."FOLDER" ("PK_FOLDER") ENABLE;
  ALTER TABLE "CUE3"."JOB" ADD CONSTRAINT "C_JOB_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_ENV
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_ENV" ADD CONSTRAINT "C_JOB_ENV_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_HISTORY" ADD CONSTRAINT "C_JOB_HISTORY_PK_DEPT" FOREIGN KEY ("PK_DEPT")
	  REFERENCES "CUE3"."DEPT" ("PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."JOB_HISTORY" ADD CONSTRAINT "C_JOB_HISTORY_PK_FACILITY" FOREIGN KEY ("PK_FACILITY")
	  REFERENCES "CUE3"."FACILITY" ("PK_FACILITY") ENABLE;
  ALTER TABLE "CUE3"."JOB_HISTORY" ADD CONSTRAINT "C_JOB_HISTORY_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_LOCAL
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_LOCAL" ADD CONSTRAINT "C_JOB_LOCAL_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;
  ALTER TABLE "CUE3"."JOB_LOCAL" ADD CONSTRAINT "C_JOB_LOCAL_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_MEM
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_MEM" ADD CONSTRAINT "C_JOB_MEM_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_POST
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_POST" ADD CONSTRAINT "C_JOB_POST_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."JOB_POST" ADD CONSTRAINT "C_JOB_POST_PK_POST_JOB" FOREIGN KEY ("PK_POST_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_RESOURCE" ADD CONSTRAINT "C_JOB_RESOURCE_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_STAT" ADD CONSTRAINT "C_JOB_STAT_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table JOB_USAGE
--------------------------------------------------------

  ALTER TABLE "CUE3"."JOB_USAGE" ADD CONSTRAINT "C_JOB_USAGE_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER" ADD CONSTRAINT "C_LAYER_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_ENV
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_ENV" ADD CONSTRAINT "C_LAYER_ENV_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_ENV" ADD CONSTRAINT "C_LAYER_ENV_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_HISTORY
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_HISTORY" ADD CONSTRAINT "C_LAYER_HISTORY_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB_HISTORY" ("PK_JOB") ON DELETE CASCADE ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_MEM
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_MEM" ADD CONSTRAINT "C_LAYER_MEM_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_MEM" ADD CONSTRAINT "C_LAYER_MEM_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_OUTPUT
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_OUTPUT" ADD CONSTRAINT "C_LAYER_OUTPUT_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_OUTPUT" ADD CONSTRAINT "C_LAYER_OUTPUT_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_RESOURCE
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_RESOURCE" ADD CONSTRAINT "C_LAYER_RESOURCE_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_RESOURCE" ADD CONSTRAINT "C_LAYER_RESOURCE_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_STAT
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_STAT" ADD CONSTRAINT "C_LAYER_STAT_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_STAT" ADD CONSTRAINT "C_LAYER_STAT_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table LAYER_USAGE
--------------------------------------------------------

  ALTER TABLE "CUE3"."LAYER_USAGE" ADD CONSTRAINT "C_LAYER_USAGE_PK_JOB" FOREIGN KEY ("PK_JOB")
	  REFERENCES "CUE3"."JOB" ("PK_JOB") ENABLE;
  ALTER TABLE "CUE3"."LAYER_USAGE" ADD CONSTRAINT "C_LAYER_USAGE_PK_LAYER" FOREIGN KEY ("PK_LAYER")
	  REFERENCES "CUE3"."LAYER" ("PK_LAYER") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table MATCHER
--------------------------------------------------------

  ALTER TABLE "CUE3"."MATCHER" ADD CONSTRAINT "C_MATCHER_PK_FILTER" FOREIGN KEY ("PK_FILTER")
	  REFERENCES "CUE3"."FILTER" ("PK_FILTER") ENABLE;

--------------------------------------------------------
--  Ref Constraints for Table OWNER
--------------------------------------------------------

  ALTER TABLE "CUE3"."OWNER" ADD CONSTRAINT "C_OWNER_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table POINT
--------------------------------------------------------

  ALTER TABLE "CUE3"."POINT" ADD CONSTRAINT "C_POINT_PK_DEPT" FOREIGN KEY ("PK_DEPT")
	  REFERENCES "CUE3"."DEPT" ("PK_DEPT") ENABLE;
  ALTER TABLE "CUE3"."POINT" ADD CONSTRAINT "C_POINT_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table PROC
--------------------------------------------------------

  ALTER TABLE "CUE3"."PROC" ADD CONSTRAINT "C_PROC_PK_FRAME" FOREIGN KEY ("PK_FRAME")
	  REFERENCES "CUE3"."FRAME" ("PK_FRAME") ENABLE;
  ALTER TABLE "CUE3"."PROC" ADD CONSTRAINT "C_PROC_PK_HOST" FOREIGN KEY ("PK_HOST")
	  REFERENCES "CUE3"."HOST" ("PK_HOST") ENABLE;


--------------------------------------------------------
--  Ref Constraints for Table SHOW_ALIAS
--------------------------------------------------------

  ALTER TABLE "CUE3"."SHOW_ALIAS" ADD CONSTRAINT "C_SHOW_ALIAS_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table SHOW_SERVICE
--------------------------------------------------------

  ALTER TABLE "CUE3"."SHOW_SERVICE" ADD CONSTRAINT "C_SHOW_SERVICE_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;

  GRANT UPDATE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT DELETE ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT INSERT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;
  GRANT SELECT ON "CUE3"."SQLN_EXPLAIN_PLAN" TO PUBLIC;

--------------------------------------------------------
--  Ref Constraints for Table SUBSCRIPTION
--------------------------------------------------------

  ALTER TABLE "CUE3"."SUBSCRIPTION" ADD CONSTRAINT "C_SUBSCRIPTION_PK_ALLOC" FOREIGN KEY ("PK_ALLOC")
	  REFERENCES "CUE3"."ALLOC" ("PK_ALLOC") ENABLE;
  ALTER TABLE "CUE3"."SUBSCRIPTION" ADD CONSTRAINT "C_SUBSCRIPTION_PK_SHOW" FOREIGN KEY ("PK_SHOW")
	  REFERENCES "CUE3"."SHOW" ("PK_SHOW") ENABLE;
--------------------------------------------------------
--  Ref Constraints for Table TASK
--------------------------------------------------------

  ALTER TABLE "CUE3"."TASK" ADD CONSTRAINT "C_TASK_PK_POINT" FOREIGN KEY ("PK_POINT")
	  REFERENCES "CUE3"."POINT" ("PK_POINT") ENABLE;




--------------------------------------------------------
--  DDL for Trigger AFTER_INSERT_FOLDER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_INSERT_FOLDER" AFTER INSERT ON folder
FOR EACH ROW
DECLARE
    int_level NUMERIC(16,0) :=0;
BEGIN
    IF :new.pk_parent_folder IS NOT NULL THEN
        SELECT folder_level.int_level + 1 INTO int_level FROM folder_level WHERE pk_folder = :new.pk_parent_folder;
    END IF;
    INSERT INTO folder_level (pk_folder_level,pk_folder,int_level) VALUES (:new.pk_folder, :new.pk_folder, int_level);
    INSERT INTO folder_resource (pk_folder_resource,pk_folder) VALUES (:new.pk_folder, :new.pk_folder);
END;

/
ALTER TRIGGER "CUE3"."AFTER_INSERT_FOLDER" ENABLE;
--------------------------------------------------------
--  DDL for Function EPOCH
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."EPOCH" 
( t IN TIMESTAMP WITH TIME ZONE
) RETURN NUMBER AS
  epoch_date TIMESTAMP(0) WITH TIME ZONE := TIMESTAMP '1970-01-01 00:00:00.00 +00:00';
  epoch_sec NUMERIC(12,0);
  delta INTERVAL DAY(9) TO SECOND(0);
BEGIN
  delta := t - epoch_date;
  RETURN INTERVAL_TO_SECONDS(delta);
END EPOCH;
 

/

--------------------------------------------------------
--  DDL for Trigger AFTER_INSERT_JOB
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_INSERT_JOB" AFTER INSERT ON job
FOR EACH ROW
BEGIN
    INSERT INTO job_stat (pk_job_stat,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_resource (pk_job_resource,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_usage (pk_job_usage,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_mem (pk_job_mem,pk_job) VALUES (:new.pk_job,:new.pk_job);
    
    INSERT INTO job_history 
        (pk_job, pk_show, pk_facility, pk_dept, str_name, str_shot, str_user, int_ts_started)
    VALUES
        (:new.pk_job, :new.pk_show, :new.pk_facility, :new.pk_dept, 
         :new.str_name, :new.str_shot, :new.str_user, epoch(systimestamp));
END;

/
ALTER TRIGGER "CUE3"."AFTER_INSERT_JOB" ENABLE;
--------------------------------------------------------
--  DDL for Trigger AFTER_INSERT_LAYER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_INSERT_LAYER" AFTER INSERT ON layer
FOR EACH ROW
BEGIN
    
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);

    INSERT INTO layer_history
        (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, b_archived)
    VALUES
        (:new.pk_layer, :new.pk_job, :new.str_name, :new.str_type, :new.int_cores_min, :new.int_mem_min, 0);
END;

/
ALTER TRIGGER "CUE3"."AFTER_INSERT_LAYER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger AFTER_JOB_DEPT_UPDATE
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_JOB_DEPT_UPDATE" AFTER UPDATE ON job
FOR EACH ROW
  WHEN (NEW.pk_dept != OLD.pk_dept AND new.str_state='Pending') DECLARE
    int_running_cores NUMERIC(16,0);
BEGIN
  /**
  * Handles the accounting for moving a job between departments.
  **/
  SELECT int_cores INTO int_running_cores
    FROM job_resource WHERE pk_job = :new.pk_job;

  IF int_running_cores > 0 THEN
    UPDATE point SET int_cores = int_cores + int_running_cores
        WHERE pk_dept = :new.pk_dept AND pk_show = :new.pk_show;
    
    UPDATE point  SET int_cores = int_cores - int_running_cores
        WHERE pk_dept = :old.pk_dept AND pk_show = :old.pk_show;
  END IF;    
    
END;

/
ALTER TRIGGER "CUE3"."AFTER_JOB_DEPT_UPDATE" ENABLE;
--------------------------------------------------------
--  DDL for Trigger AFTER_JOB_FINISHED
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_JOB_FINISHED" AFTER UPDATE ON job
FOR EACH ROW
  WHEN (old.str_state = 'Pending' AND new.str_state = 'Finished') DECLARE
    ts NUMERIC(12,0) := epoch(systimestamp);
BEGIN

    /* Sets the job history stop time */
    UPDATE
      job_history
    SET
      int_ts_stopped = ts,
      int_max_rss = (SELECT int_max_rss FROM job_mem WHERE pk_job = :new.pk_job)
    WHERE
      pk_job=:new.pk_job;
  
  /**
  * Delete any local core assignements from this job.
  **/
  DELETE FROM job_local WHERE pk_job=:new.pk_job;

END;


/
ALTER TRIGGER "CUE3"."AFTER_JOB_FINISHED" ENABLE;
--------------------------------------------------------
--  DDL for Trigger AFTER_JOB_MOVED
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."AFTER_JOB_MOVED" AFTER UPDATE ON job
FOR EACH ROW
  WHEN (NEW.pk_folder != OLD.pk_folder) DECLARE
    int_core_count NUMERIC(16,0);
BEGIN
  SELECT int_cores INTO int_core_count
  FROM job_resource WHERE pk_job = :new.pk_job;

  IF int_core_count > 0 THEN
    UPDATE folder_resource  SET int_cores = int_cores + int_core_count
    WHERE pk_folder = :new.pk_folder;
    
    UPDATE folder_resource  SET int_cores = int_cores - int_core_count
    WHERE pk_folder = :old.pk_folder;
  END IF;    
END;

/
ALTER TRIGGER "CUE3"."AFTER_JOB_MOVED" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_DELETE_FOLDER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_DELETE_FOLDER" BEFORE DELETE ON folder
FOR EACH ROW
BEGIN
    DELETE FROM folder_level WHERE pk_folder = :old.pk_folder;
    DELETE FROM folder_resource WHERE pk_folder = :old.pk_folder;
END;

/
ALTER TRIGGER "CUE3"."BEFORE_DELETE_FOLDER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_DELETE_HOST
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_DELETE_HOST" BEFORE DELETE ON host
FOR EACH ROW
BEGIN
    delete from host_stat WHERE pk_host = :old.pk_host;
    delete from host_tag WHERE pk_host = :old.pk_host;
    delete from deed WHERE pk_host = :old.pk_host;
END;

/
ALTER TRIGGER "CUE3"."BEFORE_DELETE_HOST" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_DELETE_JOB
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_DELETE_JOB" BEFORE DELETE ON job
FOR EACH ROW
DECLARE
    TYPE StatType IS RECORD (
        int_core_time_success NUMERIC(38),
        int_core_time_fail NUMERIC(38),
        int_waiting_count NUMERIC(38),
        int_dead_count NUMERIC(38),
        int_depend_count NUMERIC(38),
        int_eaten_count NUMERIC(38),
        int_succeeded_count NUMERIC(38),
        int_running_count NUMERIC(38),
        int_max_rss NUMERIC(38)
    );
    js StatType;

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
        job_mem.pk_job = :old.pk_job;

    UPDATE 
        job_history
    SET
        pk_dept = :old.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_frame_count = :old.int_frame_count,
        int_layer_count = :old.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        b_archived = 1,
        int_ts_stopped = nvl(epoch(:old.ts_stopped), epoch(systimestamp))
    WHERE
        pk_job = :old.pk_job;

    delete from depend where pk_job_depend_on=:old.pk_job or pk_job_depend_er=:old.pk_job;
    delete from frame where pk_job=:old.pk_job;
    delete from layer where pk_job=:old.pk_job;
    delete from job_env WHERE pk_job=:old.pk_job;
    delete from job_stat WHERE pk_job=:old.pk_job;
    delete from job_resource WHERE pk_job=:old.pk_job;
    delete from job_usage WHERE pk_job=:old.pk_job;
    delete from job_mem WHERE pk_job=:old.pk_job;
    delete from comments WHERE pk_job=:old.pk_job;

END;

/
ALTER TRIGGER "CUE3"."BEFORE_DELETE_JOB" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_DELETE_LAYER
--------------------------------------------------------

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
        int_max_rss NUMERIC(38)
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

/
ALTER TRIGGER "CUE3"."BEFORE_DELETE_LAYER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_INSERT_FOLDER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_INSERT_FOLDER" BEFORE INSERT ON folder
FOR EACH ROW                                                      
BEGIN
    IF :new.pk_parent_folder IS NULL THEN
        :new.b_default := 1;
    END IF;
END;

/
ALTER TRIGGER "CUE3"."BEFORE_INSERT_FOLDER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger BEFORE_INSERT_PROC
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."BEFORE_INSERT_PROC" BEFORE INSERT ON proc
FOR EACH ROW
BEGIN
  IF :new.int_cores_reserved <= 0 THEN
    Raise_application_error(-20010, 'failed to allocate proc, tried to allocate 0 cores');
  END IF;
END;

/
ALTER TRIGGER "CUE3"."BEFORE_INSERT_PROC" ENABLE;
--------------------------------------------------------
--  DDL for Package DRVDML
--------------------------------------------------------

  CREATE OR REPLACE PACKAGE "CTXSYS"."DRVDML" authid current_user as

  -- CTXCAT holding variables
  type vctab is table of varchar2(30) index by binary_integer;
  c_vctab           vctab;
  c_cttab           vctab;

  type numtab is table of number index by binary_integer;
  c_numtab          numtab;

  type dttab is table of date index by binary_integer;
  c_dttab           dttab;

  type cntab is table of varchar2(256) index by binary_integer;
  c_cntab           cntab;

  c_text_vc2        varchar2(4000);
  c_text_clob       clob;
  c_rowid           rowid;

  type updtab is table of boolean index by binary_integer;
  c_updtab          updtab;

  -- 5079472: Mirror dbms_lock constants here because dbms_lock may not
  -- be granted to public.
  s_mode number := dbms_lock.s_mode;
  x_mode number := dbms_lock.x_mode;

  -- Indicates if index population to be done on per document basis
  pv_idx_pop_per_doc    boolean := FALSE;

/*--------------------------- ProcessWaiting ------------------------------*/

procedure ProcessWaiting (
  p_idxtype in binary_integer,
  p_idxid   in number,
  p_idxown  in varchar2,
  p_idxname in varchar2,
  p_ixpid   in number,
  p_ixpname in varchar2
);

/*--------------------------- ProcessDML ------------------------*/
/*
  NAME
    ProcessDML

  DESCRIPTION
    do a sync

  ARGUMENTS
    CID             in     - column to work on
    parallel_degree in     - parallel degree
    direct_path     in     - use direct-path inserts ?

*/
procedure ProcessDML (
  p_idxid  in  number,
  p_ixpid  in  number,
  p_idxmem in  binary_integer,
  p_pardeg in  binary_integer default 1,
  p_direct_path in boolean default false,
  p_maxtime in binary_integer default 2147483647
);

/*--------------------------- MaintainKTab -------------------------*/
/*
  NAME
    MaintainKTab

  DESCRIPTION
    update the $K table after index creation/sync

  ARGUMENTS
    idx               in     - the index
    ixp               in     - the partition of the index
    p_startDocid      in     - docid to start from
    p_parallel_degree in     - parallel degree

*/
procedure MaintainKTab (
  idx         in  dr_def.idx_rec,
  ixp         in  dr_def.ixp_rec,
  p_startDocid  in  number default null,
  p_parallel_degree in number default 1
);
/*--------------------------- MaintainKTab -------------------------*/
/*
  NAME
    MaintainKTab

  DESCRIPTION
    update the $K table after index creation/sync

  ARGUMENTS
    p_idxid           in     - the index id
    p_ixpid           in     - the partition id
    p_startDocid      in     - docid to start from
    p_parallel_degree in     - parallel degree
*/
procedure MaintainKTab (
  p_idxid           in number,
  p_ixpid           in number,
  p_startDocid      in  number default null,
  p_parallel_degree in number default 1
);

/*--------------------------- DeletePending ------------------------*/

procedure DeletePending (
  p_idxid  in number,
  p_ixpid  in number,
  p_rids   in varchar2
);

/*----------------------------- CleanDML ---------------------------*/

procedure CleanDML (
  p_idxid  in number,
  p_ixpid  in number,
  p_tabid  in number
);

/*-------------------------- SetLockFailed -------------------------*/

procedure SetLockFailed (
  p_idxid  in number,
  p_ixpid  in number,
  p_rid    in rowid
);

/*--------------------------- ctxcat_dml ----------------------------*/

procedure ctxcat_dml(
  idx_owner in varchar2,
  idx_name  in varchar2,
  doindex   in boolean,
  updop     in boolean
);

/*----------------------- auto_sync_index ------------------------*/

PROCEDURE auto_sync_index(
  idx_name  in  varchar2 default NULL,
  memory    in  varchar2 default NULL,
  part_name in  varchar2 default NULL,
  parallel_degree in number default 1,
  logfile   in  varchar2 default NULL,
  events    in  number   default NULL
);

/*----------------------- com_sync_index -------------------------*/
PROCEDURE com_sync_index(
  idx_name  in  varchar2 default null,
  memory    in  varchar2 default null,
  part_name in  varchar2 default null
);

/*----------------------- add_rem_mdata --------------------------*/

PROCEDURE add_rem_mdata(
  add_rem      in varchar2,
  idx_name     in varchar2,
  section_name in varchar2,
  mdata_values in sys.odcivarchar2list,
  mdata_rowids in sys.odciridlist,
  part_name    in varchar2
);

/* 5364449: Removed csync since it is no longer used */

/*------------------- PopulatePending -----------------------------*/

PROCEDURE PopulatePending(
  idx  in dr_def.idx_rec,
  ixpname in varchar2
);

/*------------------- UpdateMDATA -----------------------------*/

PROCEDURE UpdateMDATA(
  itab     in varchar2,
  ktab     in varchar2,
  mdata_id in binary_integer,
  coltype  in varchar2,
  rid      in varchar2,
  oldval   in sys.anydata,
  newval   in sys.anydata,
  gtab     in varchar2 default null
);

/* Following 2 routines added for bug 5079472 */
/*------------------- lock_opt_rebuild ------------------------*/
PROCEDURE lock_opt_rebuild(
  cid        in number,
  pid        in number,
  lock_mode  in number,
  timeout    in number,
  release_on_commit in boolean default FALSE
);

/*----------------- unlock_opt_rebuild ------------------------*/
PROCEDURE unlock_opt_rebuild;

/*--------------------------- lock_opt_mvdata -----------------*/
PROCEDURE lock_opt_mvdata(
  cid in number,
  pid in number
);

/*-------------------- upd_sdata  -----------------------------*/
/*
  NAME
    upd_sdata

  DESCRIPTION
    update sdata section value

  ARGUMENTS
    idx_name     - index name
    section_name - SDATA section name
    sdata_value  - sdata value
    sdata_rowid  - rowid
    part_name    - partition name

  NOTES

  EXCEPTIONS
*/

PROCEDURE upd_sdata(
  idx_name      in varchar2,
  section_name  in varchar2,
  sdata_value   in sys.anydata,
  sdata_rowid   in rowid,
  part_name     in varchar2 default NULL
);

/*----------------------- ins_del_mvdata --------------------------*/
/*
  NAME
    ins_del_mvdata

  DESCRIPTION
    update a set of docids with given MVDATA values

  ARGUMENTS
    ins_del       - dml mode flag (INS, DEL, UPD)
    idx_name      - index name
    section_name  - MVDATA section name
    mvdata_values - mvdata values
    mvdata_rowids - rowids
    part_name     - partition name

  NOTES

  EXCEPTIONS
*/

PROCEDURE ins_del_mvdata(
  ins_del      in varchar2,
  idx_name     in varchar2,
  section_name in varchar2,
  mvdata_values in sys.odcinumberlist,
  mvdata_rowids in sys.odciridlist,
  part_name    in varchar2
);

/*----------------- AddRemOneMDATA ------------------------------------*/

procedure AddRemOneMDATA(
  itab    in varchar2,
  docid   in number,
  mdataid in binary_integer,
  addrem  in binary_integer,
  value   in varchar2,
  gtab    in varchar2 default null
);

/*------------------------- idx_populate_mode ------------------------- */
FUNCTION idx_populate_mode
return number;

PROCEDURE AddRemOneSDATA(
  sntab   in varchar2,
  docid   in number,
  sdataid in binary_integer,
  addrem  in binary_integer,
  value   in varchar2
);

PROCEDURE add_rem_sdata(
  add_rem      in varchar2,
  idx_name     in varchar2,
  section_name in varchar2,
  sdata_values in sys.odcivarchar2list,
  sdata_rowids in sys.odciridlist,
  part_name    in varchar2
);
end drvdml;

/

  GRANT EXECUTE ON "CTXSYS"."DRVDML" TO PUBLIC;

--------------------------------------------------------
--  DDL for Synonymn PLITBLM
--------------------------------------------------------

  CREATE OR REPLACE PUBLIC SYNONYM "PLITBLM" FOR "SYS"."PLITBLM";
--------------------------------------------------------
--  DDL for Trigger DR$I_HOST_STR_TAGSTC
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."DR$I_HOST_STR_TAGSTC" after insert or update on "CUE3"."HOST" for each row declare   reindex boolean := FALSE;   updop   boolean := FALSE; begin   ctxsys.drvdml.c_updtab.delete;   ctxsys.drvdml.c_numtab.delete;   ctxsys.drvdml.c_vctab.delete;   ctxsys.drvdml.c_rowid := :new.rowid;   if (inserting or updating('STR_TAGS') or       :new."STR_TAGS" <> :old."STR_TAGS") then     reindex := TRUE;     updop := (not inserting);     ctxsys.drvdml.c_text_vc2 := :new."STR_TAGS";   end if;   ctxsys.drvdml.c_cntab(0) := 'STR_NAME';  ctxsys.drvdml.c_cttab(0) := 'VARCHAR2';  ctxsys.drvdml.c_updtab(0) := updating('STR_NAME');   ctxsys.drvdml.c_vctab(0)  := :new."STR_NAME";  ctxsys.drvdml.ctxcat_dml('CUE3','I_HOST_STR_TAGS', reindex, updop); end;
/
ALTER TRIGGER "CUE3"."DR$I_HOST_STR_TAGSTC" ENABLE;
BEGIN 
  DBMS_DDL.SET_TRIGGER_FIRING_PROPERTY('"CUE3"','"DR$I_HOST_STR_TAGSTC"',FALSE) ; 
END;

/

--------------------------------------------------------
--  DDL for Trigger FRAME_HISTORY_OPEN
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."FRAME_HISTORY_OPEN" AFTER UPDATE ON frame
FOR EACH ROW
   WHEN (NEW.str_state != OLD.str_state) DECLARE
  str_pk_alloc VARCHAR2(36) := null;
  int_checkpoint integer := 0;
BEGIN

    IF :old.str_state = 'Running' THEN
    
        IF :new.int_exit_status = 299 THEN

          EXECUTE IMMEDIATE
          'DELETE FROM
              frame_history
          WHERE
              int_ts_stopped = 0 AND pk_frame=:1'
          USING
            :new.pk_frame;

        ELSE
          If :new.str_state = 'Checkpoint' THEN
              int_checkpoint := 1;
          END IF;
          
          EXECUTE IMMEDIATE
          'UPDATE
              frame_history
          SET
              int_mem_max_used=:1,
              int_ts_stopped=:2,
              int_exit_status=:3,
              int_checkpoint_count=:4
          WHERE
              int_ts_stopped = 0 AND pk_frame=:5'
          USING
              :new.int_mem_max_used,
              epoch(systimestamp),
              :new.int_exit_status,
              int_checkpoint,
              :new.pk_frame;
        END IF;
    END IF;
    
    IF :new.str_state = 'Running' THEN

      SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=:new.str_host;
  
      EXECUTE IMMEDIATE
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
            (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10)'
         USING :new.pk_frame,
            :new.pk_layer,
            :new.pk_job,
            :new.str_name,
            'Running',
            :new.int_cores,
            :new.int_mem_reserved,
            :new.str_host,
            epoch(systimestamp),
            str_pk_alloc;
    END IF;


EXCEPTION
    /**
    * When we first roll this out then job won't be in the historical
    * table, so frames on existing jobs will fail unless we catch
    * and eat the exceptions.
    **/
    WHEN OTHERS THEN
        NULL;
END;
/
ALTER TRIGGER "CUE3"."FRAME_HISTORY_OPEN" ENABLE;
--------------------------------------------------------
--  DDL for Function SOFT_TIER
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."SOFT_TIER" (int_cores IN NUMERIC, int_min_cores IN NUMERIC)
RETURN NUMBER AS
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

 

/

--------------------------------------------------------
--  DDL for Trigger POINT_TIER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."POINT_TIER" BEFORE UPDATE ON point
FOR EACH ROW
BEGIN
    /* calcultes a soft tier */
    :new.float_tier := soft_tier(:new.int_cores, :new.int_min_cores);
END;

/
ALTER TRIGGER "CUE3"."POINT_TIER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger TIER_FOLDER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."TIER_FOLDER" BEFORE UPDATE ON folder_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := soft_tier(:new.int_cores,:new.int_min_cores);
END;

/
ALTER TRIGGER "CUE3"."TIER_FOLDER" ENABLE;
--------------------------------------------------------
--  DDL for Function TIER
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."TIER" (int_cores IN NUMERIC, int_min_cores IN NUMERIC)
RETURN NUMBER AS
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

 

/

--------------------------------------------------------
--  DDL for Trigger TIER_HOST_LOCAL
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."TIER_HOST_LOCAL" BEFORE UPDATE ON host_local
FOR EACH ROW
BEGIN
    :new.float_tier := tier(:new.int_cores_max - :new.int_cores_idle,:new.int_cores_max);
END;


/
ALTER TRIGGER "CUE3"."TIER_HOST_LOCAL" ENABLE;
--------------------------------------------------------
--  DDL for Trigger TIER_JOB
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."TIER_JOB" BEFORE UPDATE ON job_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := tier(:new.int_cores,:new.int_min_cores);
END;

/
ALTER TRIGGER "CUE3"."TIER_JOB" ENABLE;
--------------------------------------------------------
--  DDL for Trigger TIER_SUBSCRIPTION
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."TIER_SUBSCRIPTION" BEFORE UPDATE ON subscription
FOR EACH ROW
BEGIN
    /* calcultes a soft tier */
    :new.float_tier := tier(:new.int_cores, :new.int_size);
END;

/
ALTER TRIGGER "CUE3"."TIER_SUBSCRIPTION" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_FRAME_CHECKPOINT_STATE
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_FRAME_CHECKPOINT_STATE" BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.str_state='Waiting' AND OLD.str_state='Running' AND NEW.str_checkpoint_state IN ('Enabled', 'Copying')) BEGIN
    :NEW.str_state :='Checkpoint';
END;

/
ALTER TRIGGER "CUE3"."UPDATE_FRAME_CHECKPOINT_STATE" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_FRAME_DEP_TO_WAIT
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_FRAME_DEP_TO_WAIT" BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (OLD.int_depend_count > 0 AND NEW.int_depend_count < 1 AND OLD.str_state='Depend') BEGIN
    :NEW.str_state := 'Waiting';
    :NEW.ts_updated := systimestamp;
    :NEW.int_version := :NEW.int_version + 1;
END;

/
ALTER TRIGGER "CUE3"."UPDATE_FRAME_DEP_TO_WAIT" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_FRAME_EATEN
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_FRAME_EATEN" BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.str_state='Eaten' AND OLD.str_state='Succeeded') BEGIN
    :NEW.str_state :='Succeeded';
END;

/
ALTER TRIGGER "CUE3"."UPDATE_FRAME_EATEN" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_FRAME_STATUS_COUNTS
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_FRAME_STATUS_COUNTS" AFTER UPDATE ON frame
FOR EACH ROW
  WHEN (old.str_state != 'Setup' AND old.str_state != new.str_state) DECLARE
    s_old_status_col VARCHAR2(32);
    s_new_status_col VARCHAR2(32);
BEGIN
    s_old_status_col := 'int_' || :old.str_state || '_count';
    s_new_status_col := 'int_' || :new.str_state || '_count';

    EXECUTE IMMEDIATE 'UPDATE layer_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_layer=:1' USING :new.pk_layer;
  
    EXECUTE IMMEDIATE 'UPDATE job_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_job=:1' USING :new.pk_job;    
END;

/
ALTER TRIGGER "CUE3"."UPDATE_FRAME_STATUS_COUNTS" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_FRAME_WAIT_TO_DEP
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_FRAME_WAIT_TO_DEP" BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.int_depend_count > 0 AND NEW.str_state IN ('Dead','Succeeded','Waiting','Checkpoint')) BEGIN
    :NEW.str_state := 'Depend';
    :NEW.ts_updated := systimestamp;
    :NEW.int_version := :NEW.int_version + 1;
END;

/
ALTER TRIGGER "CUE3"."UPDATE_FRAME_WAIT_TO_DEP" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPDATE_PROC_UPDATE_LAYER
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPDATE_PROC_UPDATE_LAYER" AFTER UPDATE ON proc
FOR EACH ROW
  WHEN (new.pk_layer != old.pk_layer) BEGIN
     FOR lr IN (
        SELECT
          pk_layer
        FROM
          layer_stat
        WHERE
          pk_layer IN (:old.pk_layer,:new.pk_layer)
        ORDER BY layer_stat.pk_layer DESC
        ) LOOP

      IF lr.pk_layer = :old.pk_layer THEN

        UPDATE layer_resource SET
          int_cores = int_cores - :old.int_cores_reserved
        WHERE
          pk_layer = :old.pk_layer;

      ELSE

        UPDATE layer_resource SET
          int_cores = int_cores + :new.int_cores_reserved
       WHERE
          pk_layer = :new.pk_layer;
       END IF;

    END LOOP;
END;

/
ALTER TRIGGER "CUE3"."UPDATE_PROC_UPDATE_LAYER" ENABLE;
--------------------------------------------------------
--  DDL for Trigger UPGRADE_PROC_MEMORY_USAGE
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."UPGRADE_PROC_MEMORY_USAGE" AFTER UPDATE ON proc
FOR EACH ROW
  WHEN (NEW.int_mem_reserved != OLD.int_mem_reserved) BEGIN
    UPDATE host SET 
        int_mem_idle = int_mem_idle - (:new.int_mem_reserved - :old.int_mem_reserved)
    WHERE
        pk_host = :new.pk_host;
END;

/
ALTER TRIGGER "CUE3"."UPGRADE_PROC_MEMORY_USAGE" ENABLE;
--------------------------------------------------------
--  DDL for Trigger VERIFY_HOST_LOCAL
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."VERIFY_HOST_LOCAL" BEFORE UPDATE ON host_local
FOR EACH ROW
   WHEN ((NEW.int_cores_max = OLD.int_cores_max AND NEW.int_mem_max = OLD.int_mem_max) AND
(NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle != OLD.int_mem_idle)) BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF :NEW.int_cores_idle < 0 THEN
        Raise_application_error(-20021, 'host local doesnt have enough idle cores.');
    END IF;

    IF :NEW.int_mem_idle < 0 THEN
        Raise_application_error(-20021, 'host local doesnt have enough idle memory');
    END IF;

END;
/
ALTER TRIGGER "CUE3"."VERIFY_HOST_LOCAL" ENABLE;
--------------------------------------------------------
--  DDL for Trigger VERIFY_HOST_RESOURCES
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."VERIFY_HOST_RESOURCES" BEFORE UPDATE ON host
FOR EACH ROW
   WHEN (new.int_cores_idle != old.int_cores_idle OR new.int_mem_idle != old.int_mem_idle) BEGIN
    IF :new.int_cores_idle < 0 THEN
        Raise_application_error(-20011, 'unable to allocate additional core units');
    END IF;

    If :new.int_mem_idle < 0 THEN
        Raise_application_error(-20012, 'unable to allocate additional memory');
    END IF;

    If :new.int_gpu_idle < 0 THEN
        Raise_application_error(-20013, 'unable to allocate additional gpu memory');
    END IF;

END;
/
ALTER TRIGGER "CUE3"."VERIFY_HOST_RESOURCES" ENABLE;
--------------------------------------------------------
--  DDL for Trigger VERIFY_JOB_LOCAL
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."VERIFY_JOB_LOCAL" BEFORE UPDATE ON job_local
FOR EACH ROW
  WHEN ( NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores) BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF :NEW.int_cores > :NEW.int_max_cores THEN
        Raise_application_error(-20021, 'job local has exceeded max cores');
    END IF;
END;

/
ALTER TRIGGER "CUE3"."VERIFY_JOB_LOCAL" ENABLE;
--------------------------------------------------------
--  DDL for Trigger VERIFY_JOB_RESOURCES
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."VERIFY_JOB_RESOURCES" BEFORE UPDATE ON job_resource
FOR EACH ROW
  WHEN ( NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores) BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * at the wrong time.
    **/
    IF :NEW.int_cores > :NEW.int_max_cores THEN
        Raise_application_error(-20021, 'job has exceeded max cores');
    END IF;
END;

/
ALTER TRIGGER "CUE3"."VERIFY_JOB_RESOURCES" ENABLE;
--------------------------------------------------------
--  DDL for Trigger VERIFY_SUBSCRIPTION
--------------------------------------------------------

  CREATE OR REPLACE TRIGGER "CUE3"."VERIFY_SUBSCRIPTION" BEFORE UPDATE ON subscription
FOR EACH ROW
  WHEN ( NEW.int_burst = OLD.int_burst AND NEW.int_cores > OLD.int_cores) BEGIN
    /**
    * Check to see if adding more procs will push the show over
    * its subscription size.  This check is only done when
    * new.int_burst = old.int_burst and new.int_cores > old.int cores,
    * otherwise this error would be thrown at the wrong time.
    **/
    IF :NEW.int_cores > :NEW.int_burst THEN
        Raise_application_error(-20022, 'subscription has exceeded burst size');
    END IF;
END;

/
ALTER TRIGGER "CUE3"."VERIFY_SUBSCRIPTION" ENABLE;
--------------------------------------------------------
--  DDL for View VS_ALLOC_USAGE
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_ALLOC_USAGE" ("PK_ALLOC", "INT_CORES", "INT_IDLE_CORES", "INT_RUNNING_CORES", "INT_LOCKED_CORES", "INT_AVAILABLE_CORES", "INT_HOSTS", "INT_LOCKED_HOSTS", "INT_DOWN_HOSTS") AS 
  SELECT
        alloc.pk_alloc,
        NVL(SUM(host.int_cores),0) AS int_cores,
        NVL(SUM(host.int_cores_idle),0) AS int_idle_cores,
        NVL(SUM(host.int_cores - host.int_cores_idle),0) as int_running_cores,
        NVL((SELECT SUM(int_cores) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NimbyLocked' OR str_lock_state='Locked')),0) AS int_locked_cores,
        NVL((SELECT SUM(int_cores_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='Open' AND hs.str_state ='Up'),0) AS int_available_cores,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='Locked') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='Down') AS int_down_hosts         
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc
 ;
--------------------------------------------------------
--  DDL for View VS_FOLDER_COUNTS
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_FOLDER_COUNTS" ("PK_FOLDER", "INT_DEPEND_COUNT", "INT_WAITING_COUNT", "INT_RUNNING_COUNT", "INT_DEAD_COUNT", "INT_CORES", "INT_JOB_COUNT") AS 
  SELECT
    folder.pk_folder,
    NVL(SUM(int_depend_count),0) AS int_depend_count,
    NVL(SUM(int_waiting_count),0) AS int_waiting_count,
    NVL(SUM(int_running_count),0) AS int_running_count,
    NVL(SUM(int_dead_count),0) AS int_dead_count,
    NVL(SUM(int_cores),0) AS int_cores,
    NVL(COUNT(job.pk_job),0) AS int_job_count
FROM
    folder 
      LEFT JOIN 
        job ON (folder.pk_folder = job.pk_folder AND job.str_state='Pending')
      LEFT JOIN
        job_stat ON (job.pk_job = job_stat.pk_job)
      LEFT JOIN
        job_resource ON (job.pk_job = job_resource.pk_job)
 GROUP BY 
      folder.pk_folder
 ;
--------------------------------------------------------
--  DDL for View VS_JOB_RESOURCE
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_JOB_RESOURCE" ("PK_JOB", "INT_PROCS", "INT_CORES", "INT_MEM_RESERVED") AS 
  SELECT
       job.pk_job,
       COUNT(proc.pk_proc) AS int_procs,
       COALESCE(SUM(int_cores_reserved),0) AS int_cores,
       COALESCE(SUM(int_mem_reserved),0) AS int_mem_reserved
    FROM
       cue3.job LEFT JOIN cue3.proc ON (proc.pk_job = job.pk_job)
    GROUP BY
       job.pk_job
 ;
--------------------------------------------------------
--  DDL for View VS_SHOW_RESOURCE
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_SHOW_RESOURCE" ("PK_SHOW", "INT_CORES") AS 
  SELECT
        job.pk_show,
        SUM(int_cores) AS int_cores
    FROM
       job,
       job_resource
    WHERE
       job.pk_job = job_resource.pk_job
    AND
       job.str_state='Pending'
    GROUP BY
       job.pk_show
 ;
--------------------------------------------------------
--  DDL for View VS_SHOW_STAT
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_SHOW_STAT" ("PK_SHOW", "INT_PENDING_COUNT", "INT_RUNNING_COUNT", "INT_DEAD_COUNT", "INT_JOB_COUNT") AS 
  SELECT
        job.pk_show,
        SUM(int_waiting_count+int_depend_count) AS int_pending_count,
        SUM(int_running_count) AS int_running_count,
        SUM(int_dead_count) AS int_dead_count,
        COUNT(1) AS int_job_count
    FROM
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        job.str_state = 'Pending'
    GROUP BY job.pk_show
 ;
--------------------------------------------------------
--  DDL for View VS_WAITING
--------------------------------------------------------

  CREATE OR REPLACE VIEW "CUE3"."VS_WAITING" ("PK_SHOW") AS 
  SELECT
        job.pk_show
    FROM
        job_resource jr,
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        jr.pk_job = job.pk_job
    AND
        job.str_state = 'Pending'
    AND
        job.b_paused = 0
    AND
        jr.int_max_cores - jr.int_cores >= 100 
    AND
        job_stat.int_waiting_count != 0
        
    GROUP BY job.pk_show
 ;
--------------------------------------------------------
--  DDL for Function INTERVAL_TO_SECONDS
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."INTERVAL_TO_SECONDS" 
( intrvl IN DSINTERVAL_UNCONSTRAINED
) RETURN NUMBER AS
BEGIN
   RETURN EXTRACT(DAY FROM intrvl) * 86400
         + EXTRACT(HOUR FROM intrvl) * 3600
         + EXTRACT(MINUTE FROM intrvl) * 60
         + EXTRACT(SECOND FROM intrvl);
END INTERVAL_TO_SECONDS;
 

/

--------------------------------------------------------
--  DDL for Function CALCULATE_CORE_HOURS
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."CALCULATE_CORE_HOURS" 
(int_ts_started NUMERIC, int_ts_stopped NUMERIC, 
int_start_report NUMERIC, int_stop_report NUMERIC, 
int_job_stopped NUMERIC, int_cores NUMBER)
RETURN NUMBER IS
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
 

/

--------------------------------------------------------
--  DDL for Function EPOCH_TO_TS
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."EPOCH_TO_TS" (seconds IN NUMBER)
RETURN TIMESTAMP AS
BEGIN
    RETURN TO_TIMESTAMP('19700101000000','YYYYMMDDHH24MISS TZH:TZM')
        + NUMTODSINTERVAL(seconds, 'SECOND');
END;
 

/

--------------------------------------------------------
--  DDL for Function FIND_DURATION
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."FIND_DURATION" 
(ts_started TIMESTAMP, ts_stopped TIMESTAMP)
RETURN NUMBER IS
  t_interval INTERVAL DAY TO SECOND;
  t_stopped TIMESTAMP(0);
BEGIN
    
    IF ts_started IS NULL THEN
        RETURN 0;
    END IF;

    IF ts_stopped IS NULL THEN
      t_stopped := systimestamp;
    ELSE 
      t_stopped := ts_stopped;
    END IF;

    t_interval := t_stopped - ts_started;

    RETURN ROUND((EXTRACT(DAY FROM t_interval) * 86400
        + EXTRACT(HOUR FROM t_interval) * 3600
        + EXTRACT(MINUTE FROM t_interval) * 60
        + EXTRACT(SECOND FROM t_interval)));
END;
 

/

--------------------------------------------------------
--  DDL for Function GENKEY
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."GENKEY" RETURN VARCHAR2 IS
    str_result VARCHAR2(36);
    guid VARCHAR2(36) := sys_guid();
BEGIN
    str_result := SUBSTR(guid, 0,8) || '-' || SUBSTR(guid,8,4) 
      || '-' || SUBSTR(guid,12,4) || '-' || SUBSTR(guid,16,4) || '-' || SUBSTR(guid,20,12);
    RETURN str_result;
END;
 

/

--------------------------------------------------------
--  DDL for Function RENDER_WEEKS
--------------------------------------------------------

  CREATE OR REPLACE FUNCTION "CUE3"."RENDER_WEEKS" 
(dt_end DATE)
RETURN NUMBER IS
    int_weeks NUMERIC;
BEGIN    
    int_weeks := (dt_end - (next_day(sysdate,'sunday')+7)) / 7.0;
    IF int_weeks < 1 THEN
      RETURN 1;
    ELSE
      RETURN int_weeks;
    END IF;
END;
 

/

--------------------------------------------------------
--  DDL for Procedure RECALCULATE_SUBS
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."RECALCULATE_SUBS" 
IS
BEGIN
  /**
  * concatenates all tags in host_tag and sets host.str_tags
  **/
  UPDATE subscription SET int_cores = 0;
  for r in (select proc.pk_show, alloc.pk_alloc, sum(proc.int_cores_reserved) as c from proc, host, alloc 
  where proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc
  group by proc.pk_show, alloc.pk_alloc) LOOP
      UPDATE subscription SET int_cores = r.c WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;

  END LOOP;
END;

 

/

--------------------------------------------------------
--  DDL for Procedure RECALCULATE_TAGS
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."RECALCULATE_TAGS" (str_host_id IN VARCHAR2) 
IS
  str_tag VARCHAR2(256) := '';
BEGIN
  /**
  * concatenates all tags in host_tag and sets host.str_tags
  **/
  FOR tag IN (SELECT str_tag FROM host_tag WHERE pk_host=str_host_id ORDER BY str_tag_type ASC, str_tag ASC) LOOP
    str_tag := str_tag || ' ' || tag.str_tag;
  END LOOP;
  
  EXECUTE IMMEDIATE 'UPDATE host SET str_tags=trim(:1) WHERE pk_host=:2'
    USING str_tag, str_host_id;
END;

 

/

--------------------------------------------------------
--  DDL for Procedure RECURSE_FOLDER_PARENT_CHANGE
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."RECURSE_FOLDER_PARENT_CHANGE" (str_folder_id IN VARCHAR2, str_parent_folder_id IN VARCHAR2)
IS
  int_parent_level NUMBER(38);
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

    FOR subfolder IN (SELECT pk_folder FROM folder WHERE pk_parent_folder = str_folder_id) LOOP
        cue3.recurse_folder_parent_change(subfolder.pk_folder, str_folder_id);
    END LOOP; 
END;

 

/

--------------------------------------------------------
--  DDL for Procedure RENAME_ALLOCS
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."RENAME_ALLOCS" 
IS
BEGIN
    FOR alloc IN (SELECT alloc.pk_alloc, alloc.str_name AS aname,facility.str_name AS fname FROM alloc,facility 
        WHERE alloc.pk_facility = facility.pk_facility) LOOP
        EXECUTE IMMEDIATE 'UPDATE alloc SET str_name=:1 WHERE pk_alloc=:2' USING
            alloc.fname || '.' || alloc.aname, alloc.pk_alloc;
    END LOOP;
END;
 

/

--------------------------------------------------------
--  DDL for Procedure REORDER_FILTERS
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."REORDER_FILTERS" (p_str_show_id IN VARCHAR2) IS
    f_new_order NUMBER(16,0) := 1.0;
BEGIN
    FOR r_filter IN (SELECT pk_filter FROM filter WHERE pk_show=p_str_show_id ORDER BY f_order ASC) LOOP
        UPDATE filter SET f_order=f_new_order WHERE pk_filter = r_filter.pk_filter;
        f_new_order := f_new_order + 1.0;
    END LOOP;
END;

 

/

--------------------------------------------------------
--  DDL for Procedure TMP_POPULATE_FOLDER
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."TMP_POPULATE_FOLDER" IS
BEGIN
    FOR t in (select pk_folder, pk_show, sum(int_cores) AS c from job, job_resource where job.pk_job = job_resource.pk_job GROUP by pk_folder, pk_show) LOOP
        UPDATE folder_resource SET int_cores = t.c WHERE pk_folder = t.pk_folder;
        COMMIT;
    END LOOP;
END;

 

/

--------------------------------------------------------
--  DDL for Procedure TMP_POPULATE_POINT
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."TMP_POPULATE_POINT" IS
BEGIN
    FOR t in (select pk_dept, pk_show, sum(int_cores) AS c from job, job_resource where job.pk_job = job_resource.pk_job GROUP by pk_dept, pk_show) LOOP
        UPDATE point SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_dept = t.pk_dept;
    END LOOP;
END;
 

/

--------------------------------------------------------
--  DDL for Procedure TMP_POPULATE_SUB
--------------------------------------------------------
set define off;

  CREATE OR REPLACE PROCEDURE "CUE3"."TMP_POPULATE_SUB" IS
BEGIN
    FOR t in (select proc.pk_show, host.pk_alloc, sum(int_cores_reserved) AS c from proc,host where 
        proc.pk_host = host.pk_host GROUP BY proc.pk_show, host.pk_alloc)  LOOP
        UPDATE subscription SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_alloc = t.pk_alloc;
    END LOOP;
END;

 

/

