use std::{sync::Arc, time::Duration};

use miette::Result;
use sqlx::{postgres::PgPoolOptions, Pool, Postgres, Transaction};
use tokio::sync::OnceCell;

use crate::config::CONFIG;

static CONNECTION_POOL: OnceCell<Arc<Pool<Postgres>>> = OnceCell::const_new();

/// Gets or initializes the global PostgreSQL connection pool.
///
/// Uses configuration from `CONFIG.database` to establish pool settings including
/// max connections, timeouts, and connection URL. The pool is initialized once and
/// reused for all subsequent calls.
///
/// # Returns
///
/// * `Ok(Arc<Pool<Postgres>>)` - Shared reference to the connection pool
/// * `Err(sqlx::Error)` - Failed to create or connect to the pool
pub async fn connection_pool() -> Result<Arc<Pool<Postgres>>, sqlx::Error> {
    let config = &CONFIG.database;
    CONNECTION_POOL
        .get_or_try_init(|| async {
            let pool = PgPoolOptions::new()
                .max_connections(config.pool_size)
                .idle_timeout(Duration::from_secs(30))
                .acquire_timeout(Duration::from_secs(30))
                // 1 hour. (from_hours is still an experimental feature,
                // see issue #140881 <https://github.com/rust-lang/rust/issues/140881> for more information)
                .max_lifetime(Duration::from_secs(60 * 60))
                .connect(&config.connection_url)
                .await?;
            Ok(Arc::new(pool))
        })
        .await
        .map(Arc::clone)
}

/// Begins a new database transaction from the connection pool.
///
/// # Returns
///
/// * `Ok(Transaction<'a, Postgres>)` - New database transaction
/// * `Err(sqlx::Error)` - Failed to begin transaction
pub async fn begin_transaction<'a>() -> Result<Transaction<'a, Postgres>, sqlx::Error> {
    connection_pool().await?.begin().await
}
