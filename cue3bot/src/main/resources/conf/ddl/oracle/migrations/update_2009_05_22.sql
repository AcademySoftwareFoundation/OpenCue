
/**
* Index should be unique
**/
DROP INDEX i_job_stat_pkjob;
CREATE UNIQUE INDEX i_job_stat_pk_job ON job_stat (pk_job);

/**
* Index should be unique
**/
DROP INDEX i_layerstat_pklayer;
CREATE UNIQUE INDEX i_layer_stat_pk_layer ON layer_stat (pk_layer);

/**
* Index should be unique
**/
drop index I_FOLDER_RESOURCE_PK_FOLDER;
CREATE UNIQUE INDEX i_folder_resource_pk_folder ON folder (pk_folder);      