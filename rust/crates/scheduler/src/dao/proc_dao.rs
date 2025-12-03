use futures::TryFutureExt;
use miette::{IntoDiagnostic, Result};
use sqlx::{Pool, Postgres, Transaction};
use std::sync::Arc;

use crate::{config::CONFIG, models::VirtualProc, pgpool::connection_pool};

/// Data Access Object for proc (virtual processor) operations in the job dispatch system.
///
/// A proc represents the allocation of compute resources (CPU cores, memory, GPUs) from a host
/// to execute a specific frame. This DAO manages the lifecycle of proc records in the database,
/// tracking which resources are reserved for which frames.
///
/// # Purpose
///
/// The `ProcDao` is responsible for:
/// - Creating new proc records when frames are dispatched to hosts
/// - Recording resource reservations (cores, memory, GPUs) for frame execution
/// - Maintaining the relationship between hosts, jobs, layers, frames, and allocated resources
///
/// # Database Schema
///
/// The proc table tracks:
/// - Resource identifiers (host, show, layer, job, frame)
/// - Reserved compute resources (cores, memory, GPUs)
/// - Pre-reserved and used memory tracking
/// - Local vs. remote dispatch flag
pub struct ProcDao {
    /// Shared connection pool for database operations.
    #[allow(dead_code)]
    connection_pool: Arc<Pool<Postgres>>,
}

/// SQL query to insert a new proc record into the database.
///
/// Creates a proc entry that tracks resource allocation for a frame execution.
/// The query inserts all resource reservation details including CPU cores, memory,
/// GPUs, and the relationships to host, show, layer, job, and frame.
///
/// # Parameters (Positional)
///
/// 1. `pk_proc` - Unique proc identifier (UUID)
/// 2. `pk_host` - Host ID where the proc is allocated
/// 3. `pk_show` - Show ID that owns this proc
/// 4. `pk_layer` - Layer ID within the job
/// 5. `pk_job` - Job ID that this proc belongs to
/// 6. `pk_frame` - Frame ID being executed by this proc
/// 7. `int_cores_reserved` - Number of CPU cores reserved (as hundredths)
/// 8. `int_mem_reserved` - Amount of memory reserved (bytes)
/// 9. `int_mem_pre_reserved` - Pre-reserved memory amount (bytes)
/// 10. `int_mem_used` - Initial memory usage (bytes)
/// 11. `int_gpus_reserved` - Number of GPUs reserved
/// 12. `int_gpu_mem_reserved` - GPU memory reserved (bytes)
/// 13. `int_gpu_mem_pre_reserved` - Pre-reserved GPU memory (bytes)
/// 14. `int_gpu_mem_used` - Initial GPU memory usage (bytes)
/// 15. `b_local` - Whether this is a local dispatch (boolean)
static INSERT_PROC: &str = r#"
    INSERT INTO proc (
        pk_proc,
        pk_host,
        pk_show,
        pk_layer,
        pk_job,
        pk_frame,
        int_cores_reserved,
        int_mem_reserved,
        int_mem_pre_reserved,
        int_mem_used,
        int_gpus_reserved,
        int_gpu_mem_reserved,
        int_gpu_mem_pre_reserved,
        int_gpu_mem_used,
        b_local
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
    )
"#;

impl ProcDao {
    /// Creates a new `ProcDao` instance with a connection pool.
    ///
    /// This constructor initializes the DAO by obtaining a shared database connection pool.
    /// The connection pool is reused across all operations for efficiency.
    ///
    /// # Returns
    ///
    /// Returns `Ok(ProcDao)` on success, or an error if the connection pool cannot be obtained.
    ///
    /// # Errors
    ///
    /// This function will return an error if:
    /// - The database connection pool cannot be created
    /// - Database connection parameters are invalid
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(ProcDao {
            connection_pool: pool,
        })
    }

    /// Inserts a new proc record into the database within an existing transaction.
    ///
    /// Creates a database record representing the allocation of compute resources from a host
    /// to execute a specific frame. This operation must be part of a larger transaction to
    /// ensure atomicity with other dispatch operations (e.g., updating host resources,
    /// creating frame assignments).
    ///
    /// # Arguments
    ///
    /// * `transaction` - Mutable reference to an active database transaction
    /// * `virtual_proc` - The virtual processor model containing all resource allocation details
    ///
    /// # Resource Allocation Details
    ///
    /// The function records:
    /// - **CPU Cores**: Reserved cores from the host (stored as hundredths of a core)
    /// - **Memory**: Both reserved and pre-reserved memory amounts (initialized to the same value)
    /// - **GPUs**: Number of GPUs reserved and their memory allocation
    /// - **Initial Usage**: Memory used is set to the minimum reserved amount from config
    /// - **Dispatch Type**: Whether this is a local or remote dispatch
    ///
    /// - Initial GPU memory used is set to 0
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` on successful insertion.
    ///
    /// # Errors
    ///
    /// This function will return an error if:
    /// - The SQL query execution fails (e.g., constraint violations, connection issues)
    /// - Foreign key constraints are violated (invalid host, show, layer, job, or frame IDs)
    /// - The transaction is no longer active
    pub async fn insert(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        virtual_proc: &VirtualProc,
    ) -> Result<(), (sqlx::Error, String, String)> {
        sqlx::query(INSERT_PROC)
            .bind(virtual_proc.proc_id.to_string())
            .bind(virtual_proc.host_id.to_string())
            .bind(virtual_proc.show_id.to_string())
            .bind(virtual_proc.layer_id.to_string())
            .bind(virtual_proc.job_id.to_string())
            .bind(virtual_proc.frame_id.to_string())
            .bind(virtual_proc.cores_reserved.value())
            // Memory is represented as KB on the database
            .bind(virtual_proc.memory_reserved.0 as i64 / 1024)
            .bind(virtual_proc.memory_reserved.0 as i64 / 1024)
            .bind(CONFIG.queue.mem_reserved_min.0 as i64 / 1024)
            .bind(virtual_proc.gpus_reserved as i32)
            .bind(virtual_proc.gpu_memory_reserved.0 as i64 / 1024)
            .bind(virtual_proc.gpu_memory_reserved.0 as i64 / 1024)
            .bind(0)
            .bind(virtual_proc.is_local_dispatch)
            .execute(&mut **transaction)
            .map_err(|err| {
                (
                    err,
                    virtual_proc.frame_id.to_string(),
                    virtual_proc.host_id.to_string(),
                )
            })
            .await?;

        Ok(())
    }
}
