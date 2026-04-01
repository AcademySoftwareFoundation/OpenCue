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

use std::{cmp, collections::HashMap, sync::Arc};

use miette::{Context, IntoDiagnostic, Result};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{
    dao::helpers::parse_uuid,
    models::{CoreSize, Subscription},
    pgpool::connection_pool,
};

pub type ShowId = Uuid;
pub type AllocationName = String;

/// Database model for a subscription.
///
/// Maps directly to the database schema with raw column names.
/// Should be converted to `Subscription` for business logic use.
#[derive(sqlx::FromRow)]
pub struct SubscriptionModel {
    pub pk_subscription: String,
    pub pk_alloc: String,
    pub str_alloc_name: String,
    pub pk_show: String,
    pub int_size: i64,
    pub int_burst: i64,
    pub int_cores: i32,
    pub int_gpus: i32,
}

impl From<SubscriptionModel> for Subscription {
    fn from(val: SubscriptionModel) -> Self {
        // There was a condition on cuebot in the past that would allow negative core values on
        // the subscription table. If bookedcores is negative, use 0.
        let booked_cores = cmp::max(val.int_cores, 0);

        Subscription {
            id: parse_uuid(&val.pk_subscription),
            allocation_id: parse_uuid(&val.pk_alloc),
            allocation_name: val.str_alloc_name,
            show_id: parse_uuid(&val.pk_show),
            size: val.int_size,
            burst: CoreSize::from_multiplied(
                val.int_burst.try_into().expect("int_burst should fit i32"),
            ),
            booked_cores: CoreSize::from_multiplied(booked_cores),
            booked_gpus: val.int_gpus.try_into().expect("int_gpus should fit in u32"),
        }
    }
}

//== Recompute Layer Resource
static RECOMPUTE_LAYER_RESOURCE_FROM_PROC: &str = r#"
UPDATE layer_resource lr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT lr2.pk_layer,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM layer_resource lr2
    LEFT JOIN proc p ON p.pk_layer = lr2.pk_layer
        AND ($1::text[] IS NULL OR p.pk_show = ANY($1))
    JOIN job j ON j.pk_job = lr2.pk_job AND j.str_state <> 'FINISHED'
        AND ($1::text[] IS NULL OR j.pk_show = ANY($1))
    GROUP BY lr2.pk_layer
) booked
WHERE lr.pk_layer = booked.pk_layer
  AND (lr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR lr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

//== Recompute Job Resource
static RECOMPUTE_JOB_RESOURCE_FROM_PROC: &str = r#"
UPDATE job_resource jr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT jr2.pk_job,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM job_resource jr2
    LEFT JOIN proc p ON p.pk_job = jr2.pk_job
        AND ($1::text[] IS NULL OR p.pk_show = ANY($1))
    JOIN job j ON j.pk_job = jr2.pk_job AND j.str_state <> 'FINISHED'
        AND ($1::text[] IS NULL OR j.pk_show = ANY($1))
    GROUP BY jr2.pk_job
) booked
WHERE jr.pk_job = booked.pk_job
  AND (jr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR jr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

//=== Recompute Folder Resources
static RECOMPUTE_FOLDER_RESOURCE_FROM_PROC: &str = r#"
UPDATE folder_resource fr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT fr2.pk_folder,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM folder_resource fr2
    LEFT JOIN job j ON j.pk_folder = fr2.pk_folder AND j.str_state <> 'FINISHED'
        AND ($1::text[] IS NULL OR j.pk_show = ANY($1))
    LEFT JOIN proc p ON p.pk_job = j.pk_job
        AND ($1::text[] IS NULL OR p.pk_show = ANY($1))
    GROUP BY fr2.pk_folder
) booked
WHERE fr.pk_folder = booked.pk_folder
  AND (fr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR fr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

//=== Recompute Points
static RECOMPUTE_POINT_FROM_PROC: &str = r#"
UPDATE point pt
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT pt2.pk_dept, pt2.pk_show,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM point pt2
    LEFT JOIN job j ON j.pk_dept = pt2.pk_dept AND j.str_state <> 'FINISHED'
    LEFT JOIN proc p ON p.pk_job = j.pk_job AND p.pk_show = pt2.pk_show
        AND ($1::text[] IS NULL OR p.pk_show = ANY($1))
    WHERE ($1::text[] IS NULL OR pt2.pk_show = ANY($1))
    GROUP BY pt2.pk_dept, pt2.pk_show
) booked
WHERE pt.pk_dept = booked.pk_dept
  AND pt.pk_show = booked.pk_show
  AND (pt.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR pt.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

static QUERY_SHOW_IDS_BY_NAME: &str = r#"
SELECT pk_show from show where str_name = ANY($1)
"#;

/// SQL query to recompute subscription booked cores and gpus from the proc table.
///
/// Used on scheduler startup to ensure the in-memory cache is seeded with accurate
/// booked counts, instead of relying solely on the (potentially stale) subscription table.
///
/// No facility filter is needed: each allocation belongs to exactly one facility, so
/// the join path `subscription → alloc → host → proc` naturally scopes results per
/// facility without an explicit WHERE clause.
static RECOMPUTE_BOOKED_FROM_PROC: &str = r#"
    SELECT s.pk_show, a.str_name as str_alloc_name,
           COALESCE(SUM(p.int_cores_reserved), 0)::bigint as int_cores_booked,
           COALESCE(SUM(p.int_gpus_reserved), 0)::bigint as int_gpus_booked
    FROM subscription s
    JOIN alloc a ON s.pk_alloc = a.pk_alloc
    LEFT JOIN host h ON h.pk_alloc = a.pk_alloc
    LEFT JOIN proc p ON p.pk_host = h.pk_host AND p.pk_show = s.pk_show AND p.b_local = false
    GROUP BY s.pk_show, a.str_name
"#;

/// SQL to read all subscription IDs and their current burst values.
static SELECT_SUBSCRIPTION_BURSTS: &str = r#"
    SELECT pk_subscription, int_burst FROM subscription
    WHERE ($1::text[] IS NULL OR pk_show = ANY($1))
"#;

/// Bulk-update subscription booked cores/gpus with burst bypass.
///
/// Sets `int_burst = total_cores` to prevent the `verify_subscription` trigger from
/// raising an exception when `int_cores > int_burst`. The trigger fires when
/// `NEW.int_burst = OLD.int_burst AND NEW.int_cores > OLD.int_cores`.
/// By changing `int_burst` in the same UPDATE, the trigger condition is not met.
static RECOMPUTE_SUBSCRIPTION_FROM_PROC: &str = r#"
    UPDATE subscription s
    SET int_cores = booked.total_cores,
        int_gpus = booked.total_gpus,
        int_burst = booked.total_cores
    FROM (
        SELECT s2.pk_subscription,
               COALESCE(SUM(p.int_cores_reserved), 0)::int AS total_cores,
               COALESCE(SUM(p.int_gpus_reserved), 0)::int AS total_gpus
        FROM subscription s2
        LEFT JOIN host h ON h.pk_alloc = s2.pk_alloc
        LEFT JOIN proc p ON p.pk_host = h.pk_host
                        AND p.pk_show = s2.pk_show
                        AND p.b_local = false
                        AND ($1::text[] IS NULL OR p.pk_show = ANY($1))
        WHERE ($1::text[] IS NULL OR s2.pk_show = ANY($1))
        GROUP BY s2.pk_subscription
    ) booked
    WHERE s.pk_subscription = booked.pk_subscription
      AND (s.int_cores IS DISTINCT FROM booked.total_cores
        OR s.int_gpus IS DISTINCT FROM booked.total_gpus
        OR s.int_burst IS DISTINCT FROM booked.total_cores)
"#;

/// Restore original burst values after the burst-bypass update.
static RESTORE_SUBSCRIPTION_BURSTS: &str = r#"
    UPDATE subscription s
    SET int_burst = restore.burst
    FROM (SELECT unnest($1::text[]) AS id, unnest($2::bigint[]) AS burst) restore
    WHERE s.pk_subscription = restore.id
"#;

/// SQL query to retrieve all subscriptions with their complete data.
static SELECT_ALL_SUBSCRIPTIONS: &str = r#"
    SELECT
        s.pk_subscription,
        s.pk_alloc,
        a.str_name as str_alloc_name,
        s.pk_show,
        s.int_size,
        s.int_burst,
        s.int_cores,
        s.float_tier,
        s.int_gpus
    FROM subscription s
    JOIN alloc a ON s.pk_alloc = a.pk_alloc
    ORDER BY pk_show, pk_alloc
"#;

pub struct ResourceAccountingDao {
    connection_pool: Arc<Pool<Postgres>>,
}

impl ResourceAccountingDao {
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(ResourceAccountingDao {
            connection_pool: pool,
        })
    }

    pub async fn query_show_ids_by_names(&self, show_names: Vec<String>) -> Result<Vec<Uuid>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
        }

        let show_ids_str: Vec<Row> = sqlx::query_as(QUERY_SHOW_IDS_BY_NAME)
            .bind(&show_names)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query shows by name")?;

        Ok(show_ids_str
            .iter()
            .map(|row| parse_uuid(&row.pk_show))
            .collect())
    }

    pub async fn recompute_all_from_proc(&self, show_ids: &Option<Vec<Uuid>>) -> Result<()> {
        let show_id_strings: Option<Vec<String>> = show_ids
            .as_ref()
            .map(|ids| ids.iter().map(|id| id.to_string()).collect());

        let bind_value: Option<&[String]> = show_id_strings.as_deref();
        let pool = self.connection_pool.as_ref();

        tokio::try_join!(
            async {
                sqlx::query(RECOMPUTE_LAYER_RESOURCE_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute layer resource from proc")
            },
            async {
                sqlx::query(RECOMPUTE_JOB_RESOURCE_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute job resource from proc")
            },
            async {
                sqlx::query(RECOMPUTE_FOLDER_RESOURCE_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute folder resource from proc")
            },
            async {
                sqlx::query(RECOMPUTE_POINT_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute point from proc")
            },
        )?;

        Ok(())
    }

    /// Recomputes booked core and GPU counts for all subscriptions from the proc table.
    ///
    /// Used on scheduler startup to seed the in-memory cache with accurate booked counts.
    /// Returns a map of `(show_id, allocation_name) -> (booked_cores, booked_gpus)`.
    pub async fn recompute_booked_from_proc(
        &self,
    ) -> Result<HashMap<(ShowId, AllocationName), (i64, i64)>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
            str_alloc_name: String,
            int_cores_booked: i64,
            int_gpus_booked: i64,
        }

        let rows: Vec<Row> = sqlx::query_as(RECOMPUTE_BOOKED_FROM_PROC)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute booked cores from proc table")?;

        let mut result = HashMap::new();
        for row in rows {
            let show_id = parse_uuid(&row.pk_show);
            result.insert(
                (show_id, row.str_alloc_name),
                (row.int_cores_booked, row.int_gpus_booked),
            );
        }
        Ok(result)
    }

    /// Recomputes the subscription table from the proc table using bulk SQL.
    ///
    /// Replaces the PL/pgSQL `recalculate_subs()` function with show-scoped inline SQL.
    /// Uses a transaction with three steps:
    /// 1. Read original burst values
    /// 2. Bulk update cores/gpus with burst bypass (sets burst = cores to avoid trigger)
    /// 3. Restore original burst values
    ///
    /// The `verify_subscription` trigger fires when `NEW.int_burst = OLD.int_burst AND
    /// NEW.int_cores > OLD.int_cores`, raising an exception if cores exceed burst.
    /// Step 2 changes burst in the same UPDATE so the trigger condition is never met.
    pub async fn recompute_subscription_table(&self, show_ids: &Option<Vec<Uuid>>) -> Result<()> {
        let show_id_strings: Option<Vec<String>> = show_ids
            .as_ref()
            .map(|ids| ids.iter().map(|id| id.to_string()).collect());
        let bind_value: Option<&[String]> = show_id_strings.as_deref();

        // Step 1: Save original burst values
        #[derive(sqlx::FromRow)]
        struct BurstRow {
            pk_subscription: String,
            int_burst: i64,
        }

        let mut tx = self
            .connection_pool
            .begin()
            .await
            .into_diagnostic()
            .wrap_err("Failed to begin transaction for subscription recompute")?;

        let burst_rows: Vec<BurstRow> = sqlx::query_as(SELECT_SUBSCRIPTION_BURSTS)
            .bind(bind_value)
            .fetch_all(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to read subscription burst values")?;

        let ids: Vec<String> = burst_rows
            .iter()
            .map(|r| r.pk_subscription.clone())
            .collect();
        let bursts: Vec<i64> = burst_rows.iter().map(|r| r.int_burst).collect();

        // Step 2: Bulk update cores/gpus with burst bypass
        sqlx::query(RECOMPUTE_SUBSCRIPTION_FROM_PROC)
            .bind(bind_value)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute subscription cores/gpus from proc")?;

        // Step 3: Restore original burst values
        sqlx::query(RESTORE_SUBSCRIPTION_BURSTS)
            .bind(&ids)
            .bind(&bursts)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to restore subscription burst values")?;

        tx.commit()
            .await
            .into_diagnostic()
            .wrap_err("Failed to commit subscription recompute transaction")?;

        Ok(())
    }

    /// Retrieves all subscriptions organized by show_id and allocation_name.
    pub async fn get_subscriptions_by_show(
        &self,
    ) -> Result<HashMap<ShowId, HashMap<AllocationName, Subscription>>> {
        let subscription_models: Vec<SubscriptionModel> = sqlx::query_as(SELECT_ALL_SUBSCRIPTIONS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to fetch subscriptions")?;

        let mut subscriptions_by_show: HashMap<Uuid, HashMap<String, Subscription>> =
            HashMap::new();

        for subs_model in subscription_models {
            let show_id = parse_uuid(&subs_model.pk_show);
            let allocation_name = subs_model.str_alloc_name.clone();
            let subscription = Subscription::from(subs_model);
            subscriptions_by_show
                .entry(show_id)
                .or_default()
                .insert(allocation_name, subscription);
        }

        Ok(subscriptions_by_show)
    }
}
