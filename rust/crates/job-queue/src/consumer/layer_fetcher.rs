use std::sync::Arc;

use futures::Stream;
use miette::Result;
use sqlx::{Pool, Postgres};

use crate::{config::DatabaseConfig, models::DispatchLayer, pgpool::connection_pool};

pub struct LayerFetcher {
    connection_pool: Arc<Pool<Postgres>>,
}

static QUERY_LAYER: &str = r#"
SELECT
    j.pk_job,
    j.pk_facility,
    j.str_os,
    l.int_cores_min,
    l.int_mem_min,
    l.b_threadable,
    l.int_gpus_min,
    l.int_gpu_mem_min,
    l.str_tags
FROM job j
    INNER JOIN layer l ON j.pk_job = l.pk_job
    INNER JOIN layer_stat ls on l.pk_layer = ls.pk_layer
WHERE j.pk_job = ?
    AND ls.int_waiting_count > 0
"#;

impl LayerFetcher {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(LayerFetcher {
            connection_pool: pool,
        })
    }

    pub fn query_job(
        &self,
        pk_job: String,
    ) -> impl Stream<Item = Result<DispatchLayer, sqlx::Error>> + '_ {
        sqlx::query_as::<_, DispatchLayer>(QUERY_LAYER)
            .bind(pk_job)
            .fetch(&*self.connection_pool)
    }
}
