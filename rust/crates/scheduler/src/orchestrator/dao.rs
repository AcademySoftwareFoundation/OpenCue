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

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use miette::{IntoDiagnostic, Result};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::dao::helpers::parse_uuid;

use crate::cluster::Cluster;
use crate::pgpool::connection_pool;

/// Data Access Object for orchestrator tables (scheduler_instance and scheduler_cluster_assignment).
pub struct OrchestratorDao {
    connection_pool: Arc<Pool<Postgres>>,
}

#[derive(sqlx::FromRow, Debug, Clone)]
#[allow(dead_code)]
pub struct InstanceRow {
    pub pk_instance: String,
    pub str_name: String,
    pub str_facility: Option<String>,
    pub int_capacity: i32,
    pub float_jobs_queried: f64,
    pub b_draining: bool,
}

#[derive(sqlx::FromRow, Debug, Clone)]
#[allow(dead_code)]
pub struct ClusterAssignmentRow {
    pub pk_assignment: String,
    pub pk_instance: String,
    pub str_cluster_id: String,
    pub str_cluster_json: String,
    pub int_version: i32,
}

// --- Instance queries ---

static INSERT_INSTANCE: &str = r#"
INSERT INTO scheduler_instance (pk_instance, str_name, str_facility, int_capacity, ts_heartbeat, ts_registered)
VALUES ($1, $2, $3, $4, NOW(), NOW())
"#;

static UPDATE_HEARTBEAT: &str = r#"
UPDATE scheduler_instance
SET ts_heartbeat = NOW(), float_jobs_queried = $2
WHERE pk_instance = $1
"#;

static SET_DRAINING: &str = r#"
UPDATE scheduler_instance
SET b_draining = TRUE
WHERE pk_instance = $1
"#;

static DELETE_INSTANCE: &str = r#"
DELETE FROM scheduler_instance
WHERE pk_instance = $1
"#;

static DELETE_DEAD_INSTANCES: &str = r#"
DELETE FROM scheduler_instance
WHERE ts_heartbeat < NOW() - $1::interval
RETURNING pk_instance
"#;

static QUERY_LIVE_INSTANCES: &str = r#"
SELECT pk_instance, str_name, str_facility, int_capacity, float_jobs_queried, b_draining
FROM scheduler_instance
WHERE ts_heartbeat >= NOW() - $1::interval
  AND b_draining = FALSE
"#;

// --- Cluster assignment queries ---

static QUERY_ASSIGNMENTS_FOR_INSTANCE: &str = r#"
SELECT pk_assignment, pk_instance, str_cluster_id, str_cluster_json, int_version
FROM scheduler_cluster_assignment
WHERE pk_instance = $1
"#;

static QUERY_ALL_ASSIGNMENTS: &str = r#"
SELECT pk_assignment, pk_instance, str_cluster_id, str_cluster_json, int_version
FROM scheduler_cluster_assignment
"#;

static UPSERT_ASSIGNMENT: &str = r#"
INSERT INTO scheduler_cluster_assignment (pk_instance, str_cluster_id, str_cluster_json, int_version, ts_assigned)
VALUES ($1, $2, $3, 0, NOW())
ON CONFLICT (str_cluster_id)
DO UPDATE SET pk_instance = $1, str_cluster_json = $3, int_version = scheduler_cluster_assignment.int_version + 1, ts_assigned = NOW()
"#;

static DELETE_ASSIGNMENT_BY_CLUSTER_ID: &str = r#"
DELETE FROM scheduler_cluster_assignment
WHERE str_cluster_id = $1
"#;

// --- Advisory lock ---

static TRY_ADVISORY_LOCK: &str = r#"
SELECT pg_try_advisory_lock($1)
"#;

impl OrchestratorDao {
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(OrchestratorDao {
            connection_pool: pool,
        })
    }

    // --- Instance operations ---

    pub async fn register_instance(
        &self,
        instance_id: Uuid,
        name: &str,
        facility: Option<&str>,
        capacity: i32,
    ) -> Result<(), sqlx::Error> {
        sqlx::query(INSERT_INSTANCE)
            .bind(instance_id.to_string())
            .bind(name)
            .bind(facility)
            .bind(capacity)
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    pub async fn update_heartbeat(
        &self,
        instance_id: Uuid,
        jobs_queried: f64,
    ) -> Result<(), sqlx::Error> {
        sqlx::query(UPDATE_HEARTBEAT)
            .bind(instance_id.to_string())
            .bind(jobs_queried)
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    pub async fn set_draining(&self, instance_id: Uuid) -> Result<(), sqlx::Error> {
        sqlx::query(SET_DRAINING)
            .bind(instance_id.to_string())
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    pub async fn delete_instance(&self, instance_id: Uuid) -> Result<(), sqlx::Error> {
        sqlx::query(DELETE_INSTANCE)
            .bind(instance_id.to_string())
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    pub async fn delete_dead_instances(
        &self,
        failure_threshold: Duration,
    ) -> Result<Vec<Uuid>, sqlx::Error> {
        let interval = format!("{} seconds", failure_threshold.as_secs());
        let rows: Vec<(String,)> = sqlx::query_as(DELETE_DEAD_INSTANCES)
            .bind(interval)
            .fetch_all(&*self.connection_pool)
            .await?;
        Ok(rows
            .into_iter()
            .map(|(id,)| crate::dao::helpers::parse_uuid(&id))
            .collect())
    }

    pub async fn get_live_instances(
        &self,
        failure_threshold: Duration,
    ) -> Result<HashMap<Uuid, InstanceRow>, sqlx::Error> {
        let interval = format!("{} seconds", failure_threshold.as_secs());
        let rows = sqlx::query_as::<_, InstanceRow>(QUERY_LIVE_INSTANCES)
            .bind(interval)
            .fetch_all(&*self.connection_pool)
            .await?;
        Ok(rows
            .into_iter()
            .map(|r| (parse_uuid(&r.pk_instance), r))
            .collect())
    }

    // --- Cluster assignment operations ---

    pub async fn get_assignments_for_instance(
        &self,
        instance_id: Uuid,
    ) -> Result<Vec<ClusterAssignmentRow>, sqlx::Error> {
        sqlx::query_as::<_, ClusterAssignmentRow>(QUERY_ASSIGNMENTS_FOR_INSTANCE)
            .bind(instance_id.to_string())
            .fetch_all(&*self.connection_pool)
            .await
    }

    /// Returns all cluster assignments as a map of cluster ID to assigned instance ID.
    ///
    /// The key is the stable cluster ID (e.g. `"{facility}:{show}:alloc:{tag}"`),
    /// which is independent of the exact tag content for chunked clusters.
    pub async fn get_all_assignments(&self) -> Result<HashMap<String, Uuid>, sqlx::Error> {
        let rows = sqlx::query_as::<_, ClusterAssignmentRow>(QUERY_ALL_ASSIGNMENTS)
            .fetch_all(&*self.connection_pool)
            .await?;
        Ok(rows
            .into_iter()
            .map(|r| (r.str_cluster_id, parse_uuid(&r.pk_instance)))
            .collect())
    }

    /// Upserts a cluster assignment. If the cluster is already assigned, updates the instance,
    /// refreshes the JSON content, and bumps the version.
    pub async fn upsert_assignment(
        &self,
        instance_id: Uuid,
        cluster: &Cluster,
    ) -> Result<(), sqlx::Error> {
        let cluster_json =
            serde_json::to_string(cluster).expect("Failed to serialize Cluster to JSON");
        sqlx::query(UPSERT_ASSIGNMENT)
            .bind(instance_id.to_string())
            .bind(&cluster.id)
            .bind(cluster_json)
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    pub async fn delete_assignment_by_cluster_id(
        &self,
        cluster_id: &str,
    ) -> Result<(), sqlx::Error> {
        sqlx::query(DELETE_ASSIGNMENT_BY_CLUSTER_ID)
            .bind(cluster_id)
            .execute(&*self.connection_pool)
            .await?;
        Ok(())
    }

    // --- Leader election ---

    /// Attempts to acquire the advisory lock. Returns true if acquired.
    /// Uses a dedicated connection (not from the pool) to hold the session-level lock.
    pub async fn try_acquire_leader_lock(&self, lock_id: i64) -> Result<bool, sqlx::Error> {
        let row: (bool,) = sqlx::query_as(TRY_ADVISORY_LOCK)
            .bind(lock_id)
            .fetch_one(&*self.connection_pool)
            .await?;
        Ok(row.0)
    }
}
