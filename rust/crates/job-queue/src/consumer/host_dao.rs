use std::sync::Arc;

use futures::Stream;
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::host::ThreadMode;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{
    config::DatabaseConfig,
    models::{DispatchLayer, Host},
    pgpool::connection_pool,
};

pub struct HostDao {
    connection_pool: Arc<Pool<Postgres>>,
    core_multiplier: u32,
}

#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub(crate) struct HostModel {
    pk_host: String,
    str_name: String,
    str_os: Option<String>,
    int_cores_idle: i32,
    int_mem_idle: i64,
    int_gpus_idle: i32,
    int_gpu_mem_idle: i64,
    int_cores: i32,
    int_mem: i64,
    int_thread_mode: i32,
    // Name of the allocation the host is subscribed to for a given show
    str_alloc_name: String,
    // Number of cores available at the subscription of the show this host has been queried on
    int_alloc_available_cores: i32,
    core_multiplier: i32,
}

impl From<HostModel> for Host {
    fn from(val: HostModel) -> Self {
        Host {
            id: Uuid::parse_str(&val.pk_host).unwrap_or_default(),
            name: val.str_name,
            str_os: val.str_os,
            idle_cores: (val.int_cores_idle / val.core_multiplier) as u32,
            idle_memory: val.int_mem_idle as u64,
            idle_gpus: val.int_gpus_idle as u32,
            idle_gpu_memory: val.int_gpu_mem_idle as u64,
            total_cores: (val.int_cores / val.core_multiplier) as u32,
            total_memory: val.int_mem as u64,
            thread_mode: ThreadMode::try_from(val.int_thread_mode).unwrap_or_default(),
            alloc_available_cores: (val.int_alloc_available_cores / val.core_multiplier) as u32,
            allocation_name: val.str_alloc_name,
        }
    }
}

static QUERY_DISPATCH_HOST: &str = r#"
SELECT
    h.pk_host,
    h.str_name,
    hs.str_os,
    h.int_cores_idle,
    h.int_mem_idle,
    h.int_gpus_idle,
    h.int_gpu_mem_idle,
    h.int_cores,
    h.int_mem,
    h.int_thread_mode,
    s.int_burst - s.int_cores as int_alloc_available_cores,
    a.str_name as str_alloc_name,
    ? as core_multiplier
FROM host h
    INNER JOIN host_stat hs ON h.pk_host = hs.pk_host
    INNER JOIN alloc a ON h.pk_alloc = a.pk_alloc
    INNER JOIN subscription s ON s.pk_alloc = a.pk_alloc AND s.pk_show = ?
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

impl HostDao {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(HostDao {
            connection_pool: pool,
            core_multiplier: config.core_multiplier,
        })
    }

    // Finds a host that can execute frames of a layer.
    // The returned object includes subscription and allocation data refering to the layer's
    // show subscription.
    pub fn find_host_for_layer(
        &self,
        layer: &DispatchLayer,
    ) -> impl Stream<Item = Result<HostModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, HostModel>(QUERY_DISPATCH_HOST)
            .bind(self.core_multiplier as i32)
            .bind(layer.show_id.to_string())
            .bind(layer.facility_id.to_string())
            .bind(layer.str_os.clone())
            .bind(layer.str_os.clone())
            .bind(layer.cores_min)
            .bind(layer.mem_min)
            .bind(layer.tags.clone())
            .bind(layer.gpus_min)
            .bind(layer.gpu_mem_min)
            .fetch(&*self.connection_pool)
    }

    pub async fn lock(&self, host_id: &Uuid) -> Result<bool> {
        let host_id_str = host_id.to_string();
        sqlx::query_scalar::<_, bool>("SELECT pg_try_advisory_lock(hashtext($1))")
            .bind(&host_id_str)
            .fetch_one(&*self.connection_pool)
            .await
            .into_diagnostic()
            .wrap_err("Failed to acquire advisory lock")
    }
    pub async fn unlock(&self, host_id: &Uuid) -> Result<bool> {
        let host_id_str = host_id.to_string();
        sqlx::query_scalar::<_, bool>("SELECT pg_advisory_unlock(hashtext($1))")
            .bind(&host_id_str)
            .fetch_one(&*self.connection_pool)
            .await
            .into_diagnostic()
            .wrap_err("Failed to release advisory lock")
    }
    pub async fn update_resources(&self, updated_host: &Host) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE host
            SET int_cores_idle = $1,
                int_mem_idle = $2,
                int_gpus_idle = $3,
                int_gpu_mem_idle = $4
            WHERE pk_host = $5
            "#,
        )
        .bind(updated_host.idle_cores as i32)
        .bind(updated_host.idle_memory as i64)
        .bind(updated_host.idle_gpus as i32)
        .bind(updated_host.idle_gpu_memory as i64)
        .bind(updated_host.id.to_string())
        .execute(&*self.connection_pool)
        .await
        .into_diagnostic()
        .wrap_err("Failed to update host resources")?;

        Ok(())
    }
}
