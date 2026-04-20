// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use std::sync::Arc;

use bytesize::{ByteSize, KB};
use chrono::{DateTime, Utc};
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::host::ThreadMode;
use sqlx::{Pool, Postgres, Transaction};
use thiserror::Error;
use tracing::trace;
use uuid::Uuid;

use crate::{
    config::CONFIG,
    dao::helpers::parse_uuid,
    models::{CoreSize, Host, VirtualProc},
    pgpool::connection_pool,
};

#[derive(Debug, Error)]
pub enum HostDaoError {
    #[error("Host resources exhausted (likely booked by another scheduler)")]
    HostResourcesExhausted,

    #[error("Resource limit exceeded: {message}")]
    ResourceLimitExceeded { message: String },

    #[error("{context}: {source}")]
    DbFailure {
        context: &'static str,
        source: sqlx::Error,
    },
}

/// Known PostgreSQL trigger messages that indicate expected resource limit enforcement.
const RESOURCE_LIMIT_MESSAGES: &[&str] = &[
    "job has exceeded max cores",
    "job has exceeded max GPU units",
    "subscription has exceeded burst size",
    "unable to allocate additional core units",
    "unable to allocate additional memory",
    "unable to allocate additional GPU units",
    "unable to allocate additional GPU memory",
];

fn check_resource_limit_error(err: sqlx::Error, context: &'static str) -> HostDaoError {
    let msg = err.to_string();
    match RESOURCE_LIMIT_MESSAGES.iter().find(|m| msg.contains(*m)) {
        Some(m) => HostDaoError::ResourceLimitExceeded {
            message: m.to_string(),
        },
        None => HostDaoError::DbFailure {
            context,
            source: err,
        },
    }
}

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
    pub last_updated: DateTime<Utc>,
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
    int_mem_free: i64,
    int_gpus_idle: i64,
    #[allow(dead_code)]
    int_gpu_mem_free: i64,
    int_cores: i64,
    int_mem_total: i64,
    int_thread_mode: i32,
    pk_alloc: String,
    // Name of the allocation the host is subscribed to for a given show
    str_alloc_name: String,
    // Number of cores available at the subscription of the show this host has been queried on
    int_alloc_available_cores: i64,
    ts_ping: DateTime<Utc>,
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
            idle_memory: ByteSize::kb(val.int_mem_free as u64),
            idle_gpus: val
                .int_gpus_idle
                .try_into()
                .expect("int_gpus should fit on a i32"),
            idle_gpu_memory: ByteSize::kb(val.int_gpu_mem_free as u64),
            total_cores: CoreSize::from_multiplied(
                val.int_cores
                    .try_into()
                    .expect("total_cores should fit on a i32"),
            ),
            total_memory: ByteSize::kb(val.int_mem_total as u64),
            thread_mode: ThreadMode::try_from(val.int_thread_mode).unwrap_or_default(),
            alloc_available_cores: CoreSize::from_multiplied(
                val.int_alloc_available_cores
                    .try_into()
                    .expect("alloc_available_cores should fit on a i32"),
            ),
            alloc_id: parse_uuid(&val.pk_alloc),
            alloc_name: val.str_alloc_name,
            last_updated: val.ts_ping,
        }
    }
}

// Host memory, cores and gpu values are stored at host and host_stat tables and are updated
// by different flows:
//  - memory and core fields on table host are only updated when booking procs (update_host_resources)
//  - the table host_stat contains memory fields that are updated by cuebot on HostReportHandler
//
// We use LEAST(h.int_mem_idle, hs.int_mem_free) to get the most conservative memory estimate.
// h.int_mem_idle reflects bookings (decremented on dispatch), while hs.int_mem_free reflects
// actual OS-reported free memory. Using the minimum avoids overestimating available memory
// when another scheduler (e.g. Cuebot) has booked resources that haven't been consumed yet.
static QUERY_HOST_BY_SHOW_FACILITY_AND_TAG: &str = r#"
SELECT DISTINCT
    h.pk_host,
    h.str_name,
    hs.str_os,
    h.int_cores_idle,
    LEAST(h.int_mem_idle, hs.int_mem_free) as int_mem_free,
    h.int_gpus_idle,
    LEAST(h.int_gpu_mem_idle, hs.int_gpu_mem_free) as int_gpu_mem_free,
    h.int_cores,
    hs.int_mem_total,
    h.int_thread_mode,
    s.int_burst - s.int_cores as int_alloc_available_cores,
    a.pk_alloc,
    a.str_name as str_alloc_name,
    hs.ts_ping
FROM host h
    INNER JOIN host_stat hs ON h.pk_host = hs.pk_host
    INNER JOIN alloc a ON h.pk_alloc = a.pk_alloc
    INNER JOIN subscription s ON s.pk_alloc = a.pk_alloc AND s.pk_show = $1
    INNER JOIN host_tag ht ON h.pk_host = ht.pk_host
WHERE LOWER(a.pk_facility) = LOWER($2)
    AND h.str_lock_state = 'OPEN'
    AND hs.str_state = 'UP'
    AND ht.str_tag = $3
"#;

static RESTORE_HOST_RESOURCES: &str = r#"
UPDATE host
SET int_cores_idle = int_cores_idle + $1,
    int_mem_idle = int_mem_idle + $2,
    int_gpus_idle = int_gpus_idle + $3,
    int_gpu_mem_idle = int_gpu_mem_idle + $4
WHERE pk_host = $5
    AND int_cores_idle + $1 <= int_cores
    AND int_mem_idle + $2 <= int_mem
    AND int_gpus_idle + $3 <= int_gpus
    AND int_gpu_mem_idle + $4 <= int_gpu_mem
"#;

static RESTORE_HOST_STAT: &str = r#"
UPDATE host_stat
SET int_mem_free = int_mem_free + $1,
    int_gpu_mem_free = int_gpu_mem_free + $2
WHERE pk_host = $3
"#;

static UPDATE_HOST_RESOURCES: &str = r#"
UPDATE host
SET int_cores_idle = int_cores_idle - $1,
    int_mem_idle = int_mem_idle - $2,
    int_gpus_idle = int_gpus_idle - $3,
    int_gpu_mem_idle = int_gpu_mem_idle - $4
WHERE pk_host = $5
    AND int_cores_idle >= $1
    AND int_mem_idle >= $2
    AND int_gpus_idle >= $3
    AND int_gpu_mem_idle >= $4
RETURNING int_cores_idle, int_mem_idle, int_gpus_idle, int_gpu_mem_idle, NOW()
"#;

// This update is meant for testing environments where rqd is not constantly reporting
// host reports to Cuebot to get host_stats properly updated.
static UPDATE_HOST_STAT: &str = r#"
UPDATE host_stat
SET int_mem_free = int_mem_free - $1,
    int_gpu_mem_free = int_gpu_mem_free - $2
WHERE pk_host = $3
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

    pub fn with_pool(pool: Arc<Pool<Postgres>>) -> Self {
        HostDao {
            connection_pool: pool,
        }
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
    ) -> Result<UpdatedHostResources, HostDaoError> {
        let row: Option<(i64, i64, i64, i64, DateTime<Utc>)> =
            sqlx::query_as(UPDATE_HOST_RESOURCES)
                .bind(virtual_proc.cores_reserved.value())
                .bind((virtual_proc.memory_reserved.as_u64() / KB) as i64)
                .bind(virtual_proc.gpus_reserved as i32)
                .bind(virtual_proc.gpu_memory_reserved.as_u64() as i64)
                .bind(host_id.to_string())
                .fetch_optional(&mut **transaction)
                .await
                .map_err(|err| {
                    check_resource_limit_error(err, "Failed to update host resources")
                })?;

        let (cores_idle, mem_idle, gpus_idle, gpu_mem_idle, last_updated) =
            row.ok_or(HostDaoError::HostResourcesExhausted)?;

        if CONFIG.host_cache.update_stat_on_book {
            sqlx::query(UPDATE_HOST_STAT)
                .bind((virtual_proc.memory_reserved.as_u64() / KB) as i64)
                .bind(virtual_proc.gpu_memory_reserved.as_u64() as i64)
                .bind(host_id.to_string())
                .execute(&mut **transaction)
                .await
                .map_err(|err| check_resource_limit_error(err, "Failed to update host stat"))?;
        }

        Ok(UpdatedHostResources {
            cores_idle,
            mem_idle,
            gpus_idle,
            gpu_mem_idle,
            last_updated,
        })
    }

    /// Restores host resources after a failed RQD launch.
    ///
    /// This is the reverse of `update_resources` — it adds back the cores, memory, and GPUs
    /// that were reserved during dispatch. Used during compensation when the database was
    /// committed but the RQD launch failed.
    pub async fn restore_resources(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        host_id: &Uuid,
        virtual_proc: &VirtualProc,
    ) -> Result<(), HostDaoError> {
        // Silently ignoring empty row updates here, as empty updates means resources have already
        // been reconciled either by the reconciliation scheduled job or Cuebot.
        sqlx::query(RESTORE_HOST_RESOURCES)
            .bind(virtual_proc.cores_reserved.value())
            .bind((virtual_proc.memory_reserved.as_u64() / KB) as i64)
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.gpu_memory_reserved.as_u64() as i64)
            .bind(host_id.to_string())
            .execute(&mut **transaction)
            .await
            .map_err(|err| check_resource_limit_error(err, "Failed to restore host resources"))?;

        if CONFIG.host_cache.update_stat_on_book {
            sqlx::query(RESTORE_HOST_STAT)
                .bind((virtual_proc.memory_reserved.as_u64() / KB) as i64)
                .bind(virtual_proc.gpu_memory_reserved.as_u64() as i64)
                .bind(host_id.to_string())
                .execute(&mut **transaction)
                .await
                .map_err(|err| check_resource_limit_error(err, "Failed to restore host stat"))?;
        }

        Ok(())
    }
}
