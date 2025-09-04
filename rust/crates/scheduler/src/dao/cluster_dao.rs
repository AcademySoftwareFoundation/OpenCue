use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};

use crate::{config::DatabaseConfig, pgpool::connection_pool};

/// Data Access Object for host operations in the job dispatch system.
///
/// Manages database operations related to render hosts, including:
/// - Finding suitable hosts for layer dispatch
/// - Host resource locking and unlocking
/// - Updating host resource availability after dispatch
pub struct ClusterDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// Database model representing a host with its current resource availability.
///
/// Contains host metadata, resource information, and allocation details
/// needed for dispatch matching. This model is converted to the business
/// logic `Host` type for processing.
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub(crate) struct ClusterModel {
    pub tag: String,
    pub show_id: String,
    pub facility_id: String,
    pub ttype: String,
}

static QUERY_ALLOC_CLUSTERS: &str = r#"
SELECT DISTINCT
    a.str_tag as tag,
    sh.pk_show as show_id,
    a.pk_facility as facility_id,
    'ALLOC' as ttype
FROM host_tag
    JOIN alloc a ON a.str_tag = host_tag.str_tag
    JOIN subscription sub ON sub.pk_alloc = a.pk_alloc
    JOIN show sh ON sub.pk_show = sh.pk_show
WHERE str_tag_type = 'ALLOC'
    AND sh.b_active = true
"#;

// TODO: This will not work. Each host has one entry with their hostname as a tag
// consider adding another query for str_tag_type = HOSTNAME
static QUERY_NON_ALLOC_CLUSTERS: &str = r#"
SELECT DISTINCT
    str_tag as tag,
    '' as show_id,
    '' as facility_id,
    str_tag_type as ttype
FROM host_tag
WHERE str_tag_type <> 'ALLOC'
"#;

impl ClusterDao {
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
        Ok(ClusterDao {
            connection_pool: pool,
        })
    }

    pub fn fetch_alloc_clusters(
        &self,
    ) -> impl Stream<Item = Result<ClusterModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, ClusterModel>(QUERY_ALLOC_CLUSTERS).fetch(&*self.connection_pool)
    }

    pub fn fetch_non_alloc_clusters(
        &self,
    ) -> impl Stream<Item = Result<ClusterModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, ClusterModel>(QUERY_NON_ALLOC_CLUSTERS).fetch(&*self.connection_pool)
    }
}
