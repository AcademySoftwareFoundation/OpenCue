use std::sync::Arc;

use bytesize::{ByteSize, KB};
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::host::ThreadMode;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres, Transaction};

use crate::{
    models::{CoreSize, Host},
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
pub struct HostModel {
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
            id: val.pk_host,
            name: val.str_name,
            str_os: val.str_os,
            idle_cores: CoreSize::from_multiplied(
                val.int_cores_idle
                    .try_into()
                    .expect("int_cores_min/multiplier should fit on a i32"),
            ),
            idle_memory: ByteSize::kb(val.int_mem_idle as u64),
            idle_gpus: val
                .int_gpus_idle
                .try_into()
                .expect("int_gpus should fit on a i32"),
            idle_gpu_memory: ByteSize::kb(0),
            total_cores: CoreSize::from_multiplied(
                val.int_cores
                    .try_into()
                    .expect("total_cores should fit on a i32"),
            ),
            total_memory: ByteSize::kb(val.int_mem as u64),
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

static _QUERY_DISPATCH_HOST: &str = r#"
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

static QUERY_HOST_BY_SHOW_FACILITY_AND_TAG: &str = r#"
SELECT DISTINCT
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
    INNER JOIN host_tag ht ON h.pk_host = ht.pk_host
WHERE a.pk_facility = $2
    AND h.str_lock_state = 'OPEN'
    AND hs.str_state = 'UP'
    AND ht.str_tag = $3
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
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(HostDao {
            connection_pool: pool,
        })
    }

    /// Fetches hosts matching a specific show, facility, and tag.
    ///
    /// Finds all open hosts that belong to allocations subscribed to the given show
    /// and tagged with the specified tag.
    ///
    /// # Arguments
    ///
    /// * `show_id` - UUID of the show
    /// * `facility_id` - UUID of the facility
    /// * `tag` - Tag to match against host tags
    ///
    /// # Returns
    ///
    /// * `Ok(Vec<HostModel>)` - List of matching hosts
    /// * `Err(sqlx::Error)` - Database query failed
    pub async fn fetch_hosts_by_show_facility_tag<'a>(
        &'a self,
        show_id: String,
        facility_id: String,
        tag: &'a str,
    ) -> Result<Vec<HostModel>, sqlx::Error> {
        sqlx::query_as::<_, HostModel>(QUERY_HOST_BY_SHOW_FACILITY_AND_TAG)
            .bind(show_id)
            .bind(facility_id)
            .bind(tag)
            .fetch_all(&*self.connection_pool)
            .await
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
    pub async fn lock(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        host_id: &str,
    ) -> Result<bool> {
        sqlx::query_scalar::<_, bool>("SELECT pg_try_advisory_lock(hashtext($1))")
            .bind(host_id)
            .fetch_one(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to acquire advisory lock")
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
    pub async fn unlock(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        host_id: &str,
    ) -> Result<bool> {
        let host_id_str = host_id.to_string();
        sqlx::query_scalar::<_, bool>("SELECT pg_advisory_unlock(hashtext($1))")
            .bind(&host_id_str)
            .fetch_one(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to release advisory lock")
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
    pub async fn update_resources(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        updated_host: &Host,
    ) -> Result<()> {
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
        .bind((updated_host.idle_memory.as_u64() / KB) as i64)
        .bind(updated_host.idle_gpus as i32)
        .bind(updated_host.idle_gpu_memory.as_u64() as i64)
        .bind(updated_host.id.to_string())
        .execute(&mut **transaction)
        .await
        .into_diagnostic()
        .wrap_err("Failed to update host resources")?;

        Ok(())
    }
}
