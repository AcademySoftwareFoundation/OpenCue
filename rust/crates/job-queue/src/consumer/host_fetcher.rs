use std::sync::Arc;

use futures::Stream;
use miette::Result;
use sqlx::{Pool, Postgres};

use crate::{
    config::DatabaseConfig,
    models::{DispatchLayer, HostModel},
    pgpool::connection_pool,
};

pub struct HostFetcher {
    connection_pool: Arc<Pool<Postgres>>,
}

static QUERY_DISPATCH_HOST: &str = r#"
SELECT
    h.pk_host,
    h.str_name,
    ? AS layer_threadable
FROM host h
    INNER JOIN host_stat hs ON h.pk_host = hs.pk_host
    INNER JOIN alloc ON h.pk_alloc = a.pk_alloc
WHERE a.pk_facility = ?
    AND (hs.str_os IN ? OR hs.str_os = '' and ? = '') -- review
    AND h.str_lock_state = 'OPEN'
    AND h.int_cores_idle >= ?
    AND h.int_mem_idle >= ?
    AND string_to_array(?, '|') && string_to_array(h.str_tags, ' ')
    AND h.int_gpus_idle >= ?
    AND h.int_gpu_mem_idle >= ?
ORDER BY
    -- Hosts with least resources available come first in an attempt to fully book them
    h.int_cores_idle::float / h.int_cores,
    h.int_mem_idle::float / h.int_mem
"#;

impl HostFetcher {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(HostFetcher {
            connection_pool: pool,
        })
    }

    pub fn find_host_for_job(
        &self,
        layer: &DispatchLayer,
    ) -> impl Stream<Item = Result<HostModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, HostModel>(QUERY_DISPATCH_HOST)
            .bind(layer.b_threadable)
            .bind(layer.pk_facility.clone())
            .bind(layer.str_os.clone())
            .bind(layer.str_os.clone())
            .bind(layer.int_cores_min)
            .bind(layer.int_mem_min)
            .bind(layer.str_tags.clone())
            .bind(layer.int_gpus_min)
            .bind(layer.int_gpu_mem_min)
            .fetch(&*self.connection_pool)
    }
}
