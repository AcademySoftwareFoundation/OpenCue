use std::sync::Arc;

use miette::{IntoDiagnostic, Result};
use sqlx::{Pool, Postgres, postgres::PgPoolOptions};
use tokio::sync::OnceCell;

use crate::config::DatabaseConfig;

static CONNECTION_POOL: OnceCell<Arc<Pool<Postgres>>> = OnceCell::const_new();

pub async fn connection_pool(config: &DatabaseConfig) -> Result<Arc<Pool<Postgres>>> {
    CONNECTION_POOL
        .get_or_try_init(|| async {
            let pool = PgPoolOptions::new()
                .max_connections(config.pool_size)
                .connect(&config.connection_url)
                .await
                .into_diagnostic()?;
            Ok(Arc::new(pool))
        })
        .await
        .map(Arc::clone)
}
