use std::sync::Arc;

use futures::Stream;
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::host::ThreadMode;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use tracing::trace;
use uuid::Uuid;

use crate::{
    config::DatabaseConfig,
    models::{CoreSize, DispatchLayer, Host},
    pgpool::connection_pool,
};

/// Data Access Object for host operations in the job dispatch system.
/// 
/// Manages database operations related to render hosts, including:
/// - Finding suitable hosts for layer dispatch
/// - Host resource locking and unlocking
/// - Updating host resource availability after dispatch
pub struct HostDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// Database model representing a host with its current resource availability.
/// 
/// Contains host metadata, resource information, and allocation details
/// needed for dispatch matching. This model is converted to the business
/// logic `Host` type for processing.
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub(crate) struct HostModel {
    pk_host: String,
    str_name: String,
    str_os: Option<String>,
    int_cores_idle: i64,
    int_mem_idle: i64,
    int_gpus_idle: i64,
    int_gpu_mem_idle: i64,
    int_cores: i64,
    int_mem: i64,
    int_thread_mode: i32,
    // Name of the allocation the host is subscribed to for a given show
    str_alloc_name: String,
    // Number of cores available at the subscription of the show this host has been queried on
    int_alloc_available_cores: i64,
}

impl From<HostModel> for Host {
    fn from(val: HostModel) -> Self {
        Host {
            id: Uuid::parse_str(&val.pk_host).unwrap_or_default(),
            name: val.str_name,
            str_os: val.str_os,
            idle_cores: CoreSize::from_multiplied(
                val.int_cores_idle
                    .try_into()
                    .expect("int_cores_min/multiplier should fit on a i32"),
            ),
            idle_memory: val.int_mem_idle as u64,
            idle_gpus: val
                .int_gpus_idle
                .try_into()
                .expect("int_gpus should fit on a i32"),
            idle_gpu_memory: val.int_gpu_mem_idle as u64,
            total_cores: CoreSize::from_multiplied(
                val.int_cores
                    .try_into()
                    .expect("total_cores should fit on a i32"),
            ),
            total_memory: val.int_mem as u64,
            thread_mode: ThreadMode::try_from(val.int_thread_mode).unwrap_or_default(),
            alloc_available_cores: CoreSize::from_multiplied(
                val.int_alloc_available_cores
                    .try_into()
                    .expect("alloc_available_cores should fit on a i32"),
            ),
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
    a.str_name as str_alloc_name
FROM host h
    INNER JOIN host_stat hs ON h.pk_host = hs.pk_host
    INNER JOIN alloc a ON h.pk_alloc = a.pk_alloc
    INNER JOIN subscription s ON s.pk_alloc = a.pk_alloc AND s.pk_show = $1
WHERE a.pk_facility = $2
    AND (hs.str_os ILIKE $3 OR hs.str_os = '' and $4 = '') -- review
    AND h.str_lock_state = 'OPEN'
    --AND hs.str_state = 'UP'
    AND h.int_cores_idle >= $5
    AND h.int_mem_idle >= $6
    AND string_to_array($7, ' | ') && string_to_array(h.str_tags, ' ')
    AND h.int_gpus_idle >= $8
    AND h.int_gpu_mem_idle >= $9
ORDER BY
    -- Hosts with least resources available come first in an attempt to fully book them
    h.int_cores_idle::float / h.int_cores,
    h.int_mem_idle::float / h.int_mem
LIMIT $10
"#;

impl HostDao {
    /// Creates a new HostDao from database configuration.
    /// 
    /// Establishes a connection pool to the PostgreSQL database for
    /// host-related operations.
    /// 
    /// # Arguments
    /// * `config` - Database configuration containing connection parameters
    /// 
    /// # Returns
    /// * `Ok(HostDao)` - Configured DAO ready for host operations
    /// * `Err(miette::Error)` - If database connection fails
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(HostDao {
            connection_pool: pool,
        })
    }

    /// Finds hosts capable of executing frames from a specific layer.
    /// 
    /// The query filters hosts based on:
    /// - OS compatibility (using ILIKE pattern matching)
    /// - Available resources (cores, memory, GPUs)
    /// - Host state (OPEN lock state)
    /// - Service tags compatibility
    /// - Allocation and subscription constraints
    /// 
    /// Results are ordered to prioritize hosts with fewer available resources
    /// to encourage full host utilization.
    /// 
    /// # Arguments
    /// * `layer` - The layer requiring host resources
    /// * `limit` - Maximum number of hosts to return
    /// 
    /// # Returns
    /// A stream of `HostModel` results ordered by resource utilization
    pub fn find_host_for_layer(
        &self,
        layer: &DispatchLayer,
        limit: usize,
    ) -> impl Stream<Item = Result<HostModel, sqlx::Error>> + '_ {
        let str_os_like = format!(
            "%{}%",
            layer.str_os.clone().unwrap_or("EMPTY_HOST_OS".to_string())
        );
        trace!(
            "find_host_for_layer: $1={}, $2={}, $3={}, $4={}, $5={}, $6={}, $7={}, $8={}, $9={}",
            format!("{:X}", layer.show_id),
            format!("{:X}", layer.facility_id),
            str_os_like,
            layer.str_os.clone().unwrap_or_default(),
            layer.cores_min.with_multiplier().value(),
            layer.mem_min,
            layer.tags.clone(),
            layer.gpus_min,
            layer.gpu_mem_min
        );
        sqlx::query_as::<_, HostModel>(QUERY_DISPATCH_HOST)
            .bind(format!("{:X}", layer.show_id))
            .bind(format!("{:X}", layer.facility_id))
            .bind(str_os_like)
            .bind(layer.str_os.clone().unwrap_or_default())
            .bind(layer.cores_min.with_multiplier().value())
            .bind(layer.mem_min)
            .bind(layer.tags.clone())
            .bind(layer.gpus_min)
            .bind(layer.gpu_mem_min)
            .bind(limit as i32)
            .fetch(&*self.connection_pool)
    }

    /// Acquires an advisory lock on a host to prevent concurrent dispatch.
    /// 
    /// Uses PostgreSQL's advisory lock mechanism to ensure only one dispatcher
    /// can modify a host's resources at a time. The lock is based on a hash
    /// of the host ID string.
    /// 
    /// # Arguments
    /// * `host_id` - The UUID of the host to lock
    /// 
    /// # Returns
    /// * `Ok(true)` - Lock successfully acquired
    /// * `Ok(false)` - Lock already held by another process
    /// * `Err(miette::Error)` - Database operation failed
    pub async fn lock(&self, host_id: &Uuid) -> Result<bool> {
        let host_id_str = host_id.to_string();
        sqlx::query_scalar::<_, bool>("SELECT pg_try_advisory_lock(hashtext($1))")
            .bind(&host_id_str)
            .fetch_one(&*self.connection_pool)
            .await
            .into_diagnostic()
            .wrap_err("Failed to acquire advisory lock")
        // Ok(true)
    }

    /// Releases an advisory lock on a host after dispatch completion.
    /// 
    /// Releases the PostgreSQL advisory lock that was acquired during
    /// the dispatch process, allowing other dispatchers to access the host.
    /// 
    /// # Arguments
    /// * `host_id` - The UUID of the host to unlock
    /// 
    /// # Returns
    /// * `Ok(true)` - Lock successfully released
    /// * `Ok(false)` - Lock was not held by this process
    /// * `Err(miette::Error)` - Database operation failed
    pub async fn unlock(&self, host_id: &Uuid) -> Result<bool> {
        let host_id_str = host_id.to_string();
        sqlx::query_scalar::<_, bool>("SELECT pg_advisory_unlock(hashtext($1))")
            .bind(&host_id_str)
            .fetch_one(&*self.connection_pool)
            .await
            .into_diagnostic()
            .wrap_err("Failed to release advisory lock")
        // Ok(true)
    }

    /// Updates a host's available resource counts after frame dispatch.
    /// 
    /// Modifies the host's idle resource counters in the database to reflect
    /// resources consumed by dispatched frames. This ensures accurate resource
    /// tracking for subsequent dispatch decisions.
    /// 
    /// # Arguments
    /// * `updated_host` - Host with updated idle resource values
    /// 
    /// # Returns
    /// * `Ok(())` - Resources successfully updated
    /// * `Err(miette::Error)` - Database update failed
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
        .bind(updated_host.idle_cores.with_multiplier().value())
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
