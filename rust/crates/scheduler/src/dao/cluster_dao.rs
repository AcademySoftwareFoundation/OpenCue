use std::sync::Arc;

use futures::Stream;
use miette::{IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};

use crate::pgpool::connection_pool;

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
pub struct ClusterModel {
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

static QUERY_NON_ALLOC_CLUSTERS: &str = r#"
SELECT DISTINCT
    str_tag as tag,
    '' as show_id,
    '' as facility_id,
    str_tag_type as ttype
FROM host_tag
WHERE str_tag_type <> 'ALLOC'
"#;

static QUERY_FACILITY_ID: &str = r#"
SELECT pk_facility
FROM facility
WHERE str_name = $1
"#;

static QUERY_SHOW_ID: &str = r#"
SELECT pk_show
FROM show
WHERE str_name = $1
"#;

impl ClusterDao {
    /// Creates a new HostDao from database configuration.
    ///
    /// Establishes a connection pool to the PostgreSQL database for
    /// host-related operations.
    ///
    /// # Returns
    /// * `Ok(HostDao)` - Configured DAO ready for host operations
    /// * `Err(miette::Error)` - If database connection fails
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(ClusterDao {
            connection_pool: pool,
        })
    }

    /// Fetches all allocation-based clusters from the database.
    ///
    /// Returns clusters defined by facility, show, and allocation tag combinations.
    /// Only includes active shows with host tags.
    ///
    /// # Returns
    ///
    /// * `Stream<Result<ClusterModel, sqlx::Error>>` - Stream of allocation clusters
    pub fn fetch_alloc_clusters(
        &self,
    ) -> impl Stream<Item = Result<ClusterModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, ClusterModel>(QUERY_ALLOC_CLUSTERS).fetch(&*self.connection_pool)
    }

    /// Fetches all non-allocation clusters (MANUAL and HOSTNAME tags).
    ///
    /// Returns clusters defined by manual or hostname-based tags that are not
    /// tied to specific facility/show allocations.
    ///
    /// # Returns
    ///
    /// * `Stream<Result<ClusterModel, sqlx::Error>>` - Stream of non-allocation clusters
    pub fn fetch_non_alloc_clusters(
        &self,
    ) -> impl Stream<Item = Result<ClusterModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, ClusterModel>(QUERY_NON_ALLOC_CLUSTERS).fetch(&*self.connection_pool)
    }

    /// Looks up a facility ID by facility name.
    ///
    /// # Arguments
    ///
    /// * `facility_name` - The name of the facility
    ///
    /// # Returns
    ///
    /// * `Ok(String)` - The facility ID
    /// * `Err(sqlx::Error)` - If facility not found or database error
    pub async fn get_facility_id(&self, facility_name: &str) -> Result<String, sqlx::Error> {
        let row: (String,) = sqlx::query_as(QUERY_FACILITY_ID)
            .bind(facility_name)
            .fetch_one(&*self.connection_pool)
            .await?;
        Ok(row.0)
    }

    /// Looks up a show ID by show name.
    ///
    /// # Arguments
    ///
    /// * `show_name` - The name of the show
    ///
    /// # Returns
    ///
    /// * `Ok(String)` - The show ID
    /// * `Err(sqlx::Error)` - If show not found or database error
    pub async fn get_show_id(&self, show_name: &str) -> Result<String, sqlx::Error> {
        let row: (String,) = sqlx::query_as(QUERY_SHOW_ID)
            .bind(show_name)
            .fetch_one(&*self.connection_pool)
            .await?;
        Ok(row.0)
    }
}
