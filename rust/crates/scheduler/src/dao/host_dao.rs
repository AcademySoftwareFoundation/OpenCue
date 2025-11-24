use std::sync::Arc;

use bytesize::{ByteSize, KB};
use chrono::NaiveDateTime;
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::host::ThreadMode;
use sqlx::{Pool, Postgres, Transaction};
use tracing::trace;
use uuid::Uuid;

use crate::{
    dao::helpers::parse_uuid,
    models::{CoreSize, Host, VirtualProc},
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
/// Updated resource counts after a host resource update operation.
///
/// Contains the remaining idle resources on a host after dispatch.
pub struct UpdatedHostResources {
    pub cores_idle: i64,
    pub mem_idle: i64,
    pub gpus_idle: i64,
    pub gpu_mem_idle: i64,
    pub last_updated: NaiveDateTime,
}

/// Database model representing a host with its current resource availability.
///
/// Contains host metadata, resource information, and allocation details
/// needed for dispatch matching. This model is converted to the business
/// logic `Host` type for processing.
#[derive(sqlx::FromRow)]
pub struct HostModel {
    pk_host: String,
    str_name: String,
    str_os: Option<String>,
    int_cores_idle: i64,
    int_mem_idle: i64,
    int_gpus_idle: i64,
    #[allow(dead_code)]
    int_gpu_mem_idle: i64,
    int_cores: i64,
    int_mem: i64,
    int_thread_mode: i32,
    pk_alloc: String,
    // Name of the allocation the host is subscribed to for a given show
    str_alloc_name: String,
    // Number of cores available at the subscription of the show this host has been queried on
    int_alloc_available_cores: i64,
    ts_last_updated: NaiveDateTime,
}

impl From<HostModel> for Host {
    fn from(val: HostModel) -> Self {
        Host {
            id: parse_uuid(&val.pk_host),
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
            alloc_id: parse_uuid(&val.pk_alloc),
            alloc_name: val.str_alloc_name,
            last_updated: val.ts_last_updated.and_utc(),
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
    a.pk_alloc,
    a.str_name as str_alloc_name,
    h.ts_last_updated
FROM host h
    INNER JOIN host_stat hs ON h.pk_host = hs.pk_host
    INNER JOIN alloc a ON h.pk_alloc = a.pk_alloc
    INNER JOIN subscription s ON s.pk_alloc = a.pk_alloc AND s.pk_show = $1
WHERE a.pk_facility = $2
    AND (hs.str_os ILIKE $3 OR hs.str_os = '' and $4 = '') -- review
    AND h.str_lock_state = 'OPEN'
    AND hs.str_state = 'UP'
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
    a.pk_alloc,
    a.str_name as str_alloc_name,
    h.ts_last_updated
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

static UPDATE_HOST_RESOURCES: &str = r#"
UPDATE host
SET int_cores_idle = int_cores_idle - $1,
    int_mem_idle = int_mem_idle - $2,
    int_gpus_idle = int_gpus_idle - $3,
    int_gpu_mem_idle = int_gpu_mem_idle - $4,
    ts_last_updated = CURRENT_TIMESTAMP
WHERE pk_host = $5
RETURNING int_cores_idle, int_mem_idle, int_gpus_idle, int_gpu_mem_idle, ts_last_updated
"#;

static UPDATE_SUBSCRIPTION: &str = r#"
UPDATE subscription
SET int_cores = int_cores + $1,
    int_gpus = int_gpus + $2
WHERE pk_show = $3
    AND pk_alloc = $4
"#;

static UPDATE_LAYER_RESOURCE: &str = r#"
UPDATE layer_resource
SET int_cores = int_cores + $1,
    int_gpus = int_gpus + $2
WHERE pk_layer = $3
"#;

static UPDATE_JOB_RESOURCE: &str = r#"
UPDATE job_resource
SET int_cores = int_cores + $1,
    int_gpus = int_gpus + $2
WHERE pk_job = $3
"#;

static UPDATE_FOLDER_RESOURCE: &str = r#"
UPDATE folder_resource
SET int_cores = int_cores + $1,
    int_gpus = int_gpus + $2
WHERE pk_folder = (SELECT pk_folder FROM job WHERE pk_job = $3)
"#;

static UPDATE_POINT: &str = r#"
UPDATE point
SET int_cores = int_cores + $1,
    int_gpus = int_gpus + $2
WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job = $3)
    AND pk_show = $4
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
        show_id: Uuid,
        facility_id: Uuid,
        tag: &'a str,
    ) -> Result<Vec<HostModel>, sqlx::Error> {
        let out = sqlx::query_as::<_, HostModel>(QUERY_HOST_BY_SHOW_FACILITY_AND_TAG)
            .bind(show_id.to_string())
            .bind(facility_id.to_string())
            .bind(tag)
            .fetch_all(&*self.connection_pool)
            .await;

        // TODO: Remove
        // for h in out.as_ref().expect("?") {
        //     info!("CacheFetch: {} with {} cores", h.pk_host, h.int_cores_idle);
        // }
        out
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
        host_id: &Uuid,
    ) -> Result<bool> {
        trace!("Locking {}", host_id);
        sqlx::query_scalar::<_, bool>("SELECT pg_try_advisory_lock(hashtext($1))")
            .bind(host_id.to_string())
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
        host_id: &Uuid,
    ) -> Result<bool> {
        trace!("Unlocking {}", host_id);
        sqlx::query_scalar::<_, bool>("SELECT pg_advisory_unlock(hashtext($1))")
            .bind(host_id.to_string())
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
    /// * `transaction` - Database transaction
    /// * `host_id` - ID of the host to update
    /// * `virtual_proc` - Virtual proc containing resource reservations
    ///
    /// # Returns
    /// * `Ok(UpdatedHostResources)` - Updated idle resource counts after dispatch
    /// * `Err(miette::Error)` - Database update failed
    pub async fn update_resources(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        host_id: &Uuid,
        virtual_proc: &VirtualProc,
        dispatch_id: Uuid,
    ) -> Result<UpdatedHostResources> {
        let (cores_idle, mem_idle, gpus_idle, gpu_mem_idle, last_updated): (
            i64,
            i64,
            i64,
            i64,
            NaiveDateTime,
        ) = sqlx::query_as(UPDATE_HOST_RESOURCES)
            .bind(virtual_proc.cores_reserved.value())
            .bind((virtual_proc.memory_reserved.as_u64() / KB) as i64)
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.gpu_memory_reserved.as_u64() as i64)
            .bind(host_id.to_string())
            .fetch_one(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err(format!("({dispatch_id}) Failed to update host resources"))?;

        sqlx::query(UPDATE_SUBSCRIPTION)
            .bind(virtual_proc.cores_reserved.value())
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.show_id.to_string())
            .bind(virtual_proc.alloc_id.to_string())
            .execute(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to update subscription resources")?;

        sqlx::query(UPDATE_LAYER_RESOURCE)
            .bind(virtual_proc.cores_reserved.value())
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.layer_id.to_string())
            .execute(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to update layer resources")?;

        sqlx::query(UPDATE_JOB_RESOURCE)
            .bind(virtual_proc.cores_reserved.value())
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.job_id.to_string())
            .execute(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to update job resources")?;

        sqlx::query(UPDATE_FOLDER_RESOURCE)
            .bind(virtual_proc.cores_reserved.value())
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.job_id.to_string())
            .execute(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to update folder resources")?;

        sqlx::query(UPDATE_POINT)
            .bind(virtual_proc.cores_reserved.value())
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.job_id.to_string())
            .bind(virtual_proc.show_id.to_string())
            .execute(&mut **transaction)
            .await
            .into_diagnostic()
            .wrap_err("Failed to update point resources")?;

        Ok(UpdatedHostResources {
            cores_idle,
            mem_idle,
            gpus_idle,
            gpu_mem_idle,
            last_updated,
        })
    }
}
