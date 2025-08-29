use std::sync::Arc;

use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{cluster::Cluster, config::DatabaseConfig, pgpool::connection_pool};

#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct SubscriptionModel {
    pub pk_subscription: String,
    pub pk_alloc: String,
    pub str_alloc_name: String,
    pub pk_show: String,
    pub str_show_name: String,
}

impl From<SubscriptionModel> for Cluster {
    fn from(value: SubscriptionModel) -> Self {
        Cluster::new(
            Uuid::parse_str(&value.pk_subscription).unwrap_or_default(),
            Uuid::parse_str(&value.pk_show).unwrap_or_default(),
            value.str_show_name,
            Uuid::parse_str(&value.pk_alloc).unwrap_or_default(),
            value.str_alloc_name,
            // TODO: Query all tags on host_tags for all hosts on this subscription
        )
    }
}

pub struct SubscriptionDao {
    connection_pool: Arc<Pool<Postgres>>,
}

static QUERY_SUBSCRIPTION: &str = r#"
SELECT
    s.pk_subscription
    a.pk_alloc,
    a.str_name as str_alloc_name,
    s.pk_show,
    s.str_name as str_show_name
FROM
    subscription sub
    INNER JOIN show s ON sub.pk_show = s.pk_show
    INNER JOIN alloc a ON sub.pk_alloc = a.pk_alloc
WHERE
    a.b_enabled = 1
    AND s.b_active = 1
"#;

impl SubscriptionDao {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(SubscriptionDao {
            connection_pool: pool,
        })
    }
    pub async fn fetch_active(&self) -> Result<Vec<SubscriptionModel>, sqlx::Error> {
        sqlx::query_as::<_, SubscriptionModel>(QUERY_SUBSCRIPTION)
            .fetch_all(&*self.connection_pool)
            .await
    }
}
