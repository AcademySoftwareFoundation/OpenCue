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
    /// `pk_alloc` UUID (as text) for `'ALLOC'` rows; `NULL` for non-alloc rows.
    /// Carried through so `Tag::alloc_id` can be populated on the ALLOC arm of
    /// `cluster.rs::load_clusters`, enabling the matcher's pre-checkout
    /// subscription burst snapshot.
    pub alloc_id: Option<String>,
}

// Only shows flagged `b_scheduler_managed = true` are owned by the scheduler;
// every cluster query is scoped to those shows. Cuebot owns the rest.
static QUERY_ALLOC_CLUSTERS: &str = r#"
SELECT DISTINCT
    a.str_tag as tag,
    a.pk_alloc as alloc_id,
    sh.pk_show as show_id,
    a.pk_facility as facility_id,
    'ALLOC' as ttype
FROM host_tag
    JOIN alloc a ON a.str_tag = host_tag.str_tag
    JOIN subscription sub ON sub.pk_alloc = a.pk_alloc
    JOIN show sh ON sub.pk_show = sh.pk_show
WHERE str_tag_type = 'ALLOC'
    AND sh.b_active = true
    AND sh.b_scheduler_managed = true
"#;

static QUERY_ALLOC_CLUSTERS_WITH_FACILITY: &str = r#"
SELECT DISTINCT
    a.str_tag as tag,
    a.pk_alloc as alloc_id,
    sh.pk_show as show_id,
    a.pk_facility as facility_id,
    'ALLOC' as ttype
FROM host_tag
    JOIN alloc a ON a.str_tag = host_tag.str_tag
    JOIN subscription sub ON sub.pk_alloc = a.pk_alloc
    JOIN show sh ON sub.pk_show = sh.pk_show
WHERE str_tag_type = 'ALLOC'
    AND sh.b_active = true
    AND sh.b_scheduler_managed = true
    AND a.pk_facility = $1
"#;

// As this query is not filtered by show, each show+subscription will
// return a row, meaning repeated tags are returned, but each one bound
// to their own show
static QUERY_NON_ALLOC_CLUSTERS: &str = r#"
SELECT DISTINCT
    host_tag.str_tag as tag,
    NULL::text as alloc_id,
    s.pk_show as show_id,
    a.pk_facility as facility_id,
    str_tag_type as ttype
FROM host_tag
JOIN host h on h.pk_host = host_tag.pk_host
JOIN alloc a ON a.pk_alloc = h.pk_alloc
JOIN subscription s ON a.pk_alloc = s.pk_alloc
JOIN show sh ON sh.pk_show = s.pk_show
WHERE str_tag_type <> 'ALLOC'
    AND sh.b_active = true
    AND sh.b_scheduler_managed = true
"#;

static QUERY_NON_ALLOC_CLUSTERS_WITH_FACILITY: &str = r#"
SELECT DISTINCT
    host_tag.str_tag as tag,
    NULL::text as alloc_id,
    s.pk_show as show_id,
    a.pk_facility as facility_id,
    str_tag_type as ttype
FROM host_tag
JOIN host h on h.pk_host = host_tag.pk_host
JOIN alloc a ON a.pk_alloc = h.pk_alloc
JOIN subscription s ON a.pk_alloc = s.pk_alloc
JOIN show sh ON sh.pk_show = s.pk_show
WHERE str_tag_type <> 'ALLOC'
    AND sh.b_active = true
    AND sh.b_scheduler_managed = true
    AND a.pk_facility = $1
"#;

static QUERY_FACILITY_ID: &str = r#"
SELECT pk_facility
FROM facility
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

    /// Fetches all allocation-based clusters for scheduler-managed shows.
    ///
    /// Returns clusters defined by facility, show, and allocation tag combinations.
    /// Only includes active shows where `b_scheduler_managed = true`.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Optional facility ID to filter clusters to a specific facility
    ///
    /// # Returns
    ///
    /// * `Stream<Result<ClusterModel, sqlx::Error>>` - Stream of allocation clusters
    pub fn fetch_alloc_clusters(
        &self,
        facility_id: Option<String>,
    ) -> std::pin::Pin<Box<dyn Stream<Item = Result<ClusterModel, sqlx::Error>> + Send + '_>> {
        match facility_id {
            Some(fid) => Box::pin(
                sqlx::query_as::<_, ClusterModel>(QUERY_ALLOC_CLUSTERS_WITH_FACILITY)
                    .bind(fid)
                    .fetch(&*self.connection_pool),
            ),
            None => Box::pin(
                sqlx::query_as::<_, ClusterModel>(QUERY_ALLOC_CLUSTERS)
                    .fetch(&*self.connection_pool),
            ),
        }
    }

    /// Fetches all non-allocation clusters (MANUAL, HOSTNAME, HARDWARE tags) for
    /// scheduler-managed shows.
    ///
    /// Returns clusters defined by non-allocation host tags tied to their
    /// specific facility/show, scoped to shows where `b_scheduler_managed = true`.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Optional facility ID to filter clusters to a specific facility
    ///
    /// # Returns
    ///
    /// * `Stream<Result<ClusterModel, sqlx::Error>>` - Stream of non-allocation clusters
    pub fn fetch_non_alloc_clusters(
        &self,
        facility_id: Option<String>,
    ) -> std::pin::Pin<Box<dyn Stream<Item = Result<ClusterModel, sqlx::Error>> + Send + '_>> {
        match facility_id {
            Some(fid) => Box::pin(
                sqlx::query_as::<_, ClusterModel>(QUERY_NON_ALLOC_CLUSTERS_WITH_FACILITY)
                    .bind(fid)
                    .fetch(&*self.connection_pool),
            ),
            None => Box::pin(
                sqlx::query_as::<_, ClusterModel>(QUERY_NON_ALLOC_CLUSTERS)
                    .fetch(&*self.connection_pool),
            ),
        }
    }

    /// Looks up a facility ID by facility name.
    ///
    /// # Arguments
    ///
    /// * `facility_name` - The name of the facility
    ///
    /// # Returns
    ///
    /// * `Ok(String)` - The facility ID (verbatim from the DB, canonical casing)
    /// * `Err(sqlx::Error)` - If facility not found or database error
    pub async fn get_facility_id(&self, facility_name: &str) -> Result<String, sqlx::Error> {
        let row: (String,) = sqlx::query_as(QUERY_FACILITY_ID)
            .bind(facility_name)
            .fetch_one(&*self.connection_pool)
            .await?;
        Ok(row.0)
    }
}
