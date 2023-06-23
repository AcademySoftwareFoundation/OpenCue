Insert into SHOW (PK_SHOW,STR_NAME,INT_DEFAULT_MAX_CORES,INT_DEFAULT_MIN_CORES,B_BOOKING_ENABLED,B_DISPATCH_ENABLED,B_ACTIVE) values ('00000000-0000-0000-0000-000000000000', 'testing', 200000, 100, true, true, true);

Insert into SHOW_STATS (PK_SHOW,INT_FRAME_INSERT_COUNT,INT_JOB_INSERT_COUNT,INT_FRAME_SUCCESS_COUNT,INT_FRAME_FAIL_COUNT) values ('00000000-0000-0000-0000-000000000000',0,0,0,0)

Insert into SHOW_ALIAS (PK_SHOW_ALIAS,PK_SHOW,STR_NAME) values ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000000', 'test');


Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0', 'Lighting', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1', 'Animation', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA2', 'Hair', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA3', 'Cloth', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA4', 'Layout', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA5', 'FX', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA6', 'Pipeline', false);

Insert into DEPT (PK_DEPT,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA7', 'Unknown', true);


Insert into FACILITY (PK_FACILITY,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1', 'local', false);

Insert into FACILITY (PK_FACILITY,STR_NAME,B_DEFAULT) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0', 'cloud', true);


Insert into FOLDER (PK_FOLDER,PK_PARENT_FOLDER,PK_SHOW,STR_NAME,B_DEFAULT,PK_DEPT,INT_JOB_MIN_CORES,INT_JOB_MAX_CORES,INT_JOB_PRIORITY,F_ORDER,B_EXCLUDE_MANAGED) values ('A0000000-0000-0000-0000-000000000000',null,'00000000-0000-0000-0000-000000000000','testing', true ,'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA6',-1,-1,-1,1, false);


Insert into POINT (PK_POINT,PK_DEPT,PK_SHOW,STR_TI_TASK,INT_CORES,B_MANAGED,INT_MIN_CORES,FLOAT_TIER) values ('FFEEDDCC-AAAA-AAAA-AAAA-AAAAAAAAAAA0','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA6','00000000-0000-0000-0000-000000000000',null,0,false,0,0);


Insert into ALLOC (PK_ALLOC,STR_NAME,B_ALLOW_EDIT,B_DEFAULT,STR_TAG,PK_FACILITY,B_BILLABLE,B_ENABLED) values ('00000000-0000-0000-0000-000000000000','local.general',false,true,'general','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1',false,true);

Insert into ALLOC (PK_ALLOC,STR_NAME,B_ALLOW_EDIT,B_DEFAULT,STR_TAG,PK_FACILITY,B_BILLABLE,B_ENABLED) values ('00000000-0000-0000-0000-000000000001','local.desktop',false, false,'desktop','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1',false,true);

Insert into ALLOC (PK_ALLOC,STR_NAME,B_ALLOW_EDIT,B_DEFAULT,STR_TAG,PK_FACILITY,B_BILLABLE,B_ENABLED) values ('00000000-0000-0000-0000-000000000002','local.unassigned',false,false,'unassigned','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1',false,true);

Insert into ALLOC (PK_ALLOC,STR_NAME,B_ALLOW_EDIT,B_DEFAULT,STR_TAG,PK_FACILITY,B_BILLABLE,B_ENABLED) values ('00000000-0000-0000-0000-000000000003','cloud.general',true,false,'general','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0',false,true);

Insert into ALLOC (PK_ALLOC,STR_NAME,B_ALLOW_EDIT,B_DEFAULT,STR_TAG,PK_FACILITY,B_BILLABLE,B_ENABLED) values ('00000000-0000-0000-0000-000000000004','cloud.unassigned',true,false,'unassigned','AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0',false,true);


Insert into SUBSCRIPTION (PK_SUBSCRIPTION,PK_ALLOC,PK_SHOW,INT_SIZE,INT_BURST,INT_CORES,FLOAT_TIER) values ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000',100000,100000,0,0);

Insert into SUBSCRIPTION (PK_SUBSCRIPTION,PK_ALLOC,PK_SHOW,INT_SIZE,INT_BURST,INT_CORES,FLOAT_TIER) values ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000000',100000,100000,0,0);

Insert into SUBSCRIPTION (PK_SUBSCRIPTION,PK_ALLOC,PK_SHOW,INT_SIZE,INT_BURST,INT_CORES,FLOAT_TIER) values ('00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000000',100000,100000,0,0);


Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0','default',false,100,3355443,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1','prman',false,100,3355443,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA2','arnold',true,100,3355443,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA3','shell',false,100,3355443,'general | util');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA4','maya',false,100,2097152,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA5','houdini',false,100,3355443,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA7','katana',true,100,2097152,'general | desktop | util');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA9','nuke',false,100,2097152,'general | desktop');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA11','preprocess',false,10,393216,'util');

Insert into SERVICE (PK_SERVICE,STR_NAME,B_THREADABLE,INT_CORES_MIN,INT_MEM_MIN,STR_TAGS) values ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA12','postprocess',false,10,524288,'util');


Insert into CONFIG (PK_CONFIG,STR_KEY,INT_VALUE,LONG_VALUE,STR_VALUE,B_VALUE) values ('00000000-0000-0000-0000-000000000005','MAX_FRAME_RETRIES',16,0,null,false);


Insert into TASK_LOCK (PK_TASK_LOCK,STR_NAME,INT_LOCK,INT_TIMEOUT) values ('00000000-0000-0000-0000-000000000002','LOCK_HARDWARE_STATE_CHECK',0,30);

Insert into TASK_LOCK (PK_TASK_LOCK,STR_NAME,INT_LOCK,INT_TIMEOUT) values ('00000000-0000-0000-0000-000000000001','LOCK_HISTORICAL_TRANSFER',0,3600);

Insert into TASK_LOCK (PK_TASK_LOCK,STR_NAME,INT_LOCK,INT_TIMEOUT) values ('00000000-0000-0000-0000-000000000003','LOCK_ORPHANED_PROC_CHECK',0,30);

Insert into TASK_LOCK (PK_TASK_LOCK,STR_NAME,INT_LOCK,INT_TIMEOUT) values ('00000000-0000-0000-0000-000000000005','LOCK_TASK_UPDATE',1240618998852,3600);
