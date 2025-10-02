use std::{sync::Arc, time::Duration};

use miette::Result;
use sqlx::{Pool, Postgres, Transaction, postgres::PgPoolOptions};
use tokio::sync::OnceCell;

use crate::config::CONFIG;

static CONNECTION_POOL: OnceCell<Arc<Pool<Postgres>>> = OnceCell::const_new();

pub async fn connection_pool() -> Result<Arc<Pool<Postgres>>, sqlx::Error> {
    let config = &CONFIG.database;
    CONNECTION_POOL
        .get_or_try_init(|| async {
            let pool = PgPoolOptions::new()
                .max_connections(config.pool_size)
                .idle_timeout(Duration::from_secs(30))
                .acquire_timeout(Duration::from_secs(30))
                .max_lifetime(Duration::from_hours(1))
                .connect(&config.connection_url)
                .await?;
            Ok(Arc::new(pool))
        })
        .await
        .map(Arc::clone)
}

pub async fn begin_transaction<'a>() -> Result<Transaction<'a, Postgres>, sqlx::Error> {
    connection_pool().await?.begin().await
}
