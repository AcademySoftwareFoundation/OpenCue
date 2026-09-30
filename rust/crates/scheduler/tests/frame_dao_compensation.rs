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

//! Standalone integration test for the dispatch-compensation frame-version fix (Bug 2).
//!
//! Self-contained on purpose - it seeds its own minimal facility -> ... -> frame chain and
//! does NOT depend on the cluster/Tag fixtures in `smoke_tests.rs`, so it compiles and runs
//! independently. Gated behind the `smoke-tests` feature; requires the repo-root
//! `docker compose up -d flyway` Postgres (host `localhost:5432`, db/user `cuebot`).
//!
//! Run with: `cargo test -p scheduler --features smoke-tests --test frame_dao_compensation`.

#[cfg(feature = "smoke-tests")]
mod util;

#[cfg(feature = "smoke-tests")]
mod frame_dao_compensation {
    use std::sync::Arc;

    use scheduler::dao::FrameDao;
    use serial_test::serial;
    use sqlx::{Pool, Postgres};
    use uuid::Uuid;

    use crate::util::test_connection_pool;

    /// Seeds a minimal facility -> dept -> show -> folder -> job -> layer -> frame chain with
    /// a single WAITING frame. Column lists and values mirror the `smoke_tests` harness.
    /// Returns the frame id and the unique row-name prefix used for cleanup.
    async fn seed_one_waiting_frame(pool: &Pool<Postgres>) -> Result<(Uuid, String), sqlx::Error> {
        let suffix = Uuid::new_v4().to_string()[..8].to_string();
        let prefix = format!("integ_test_compfix_{}", suffix);

        let facility_id = Uuid::new_v4();
        let dept_id = Uuid::new_v4();
        let show_id = Uuid::new_v4();
        let folder_id = Uuid::new_v4();
        let job_id = Uuid::new_v4();
        let layer_id = Uuid::new_v4();
        let frame_id = Uuid::new_v4();

        let mut tx = pool.begin().await?;

        sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
            .bind(facility_id.to_string())
            .bind(format!("{}_facility", prefix))
            .execute(&mut *tx)
            .await?;

        sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
            .bind(dept_id.to_string())
            .bind(format!("{}_dept", prefix))
            .execute(&mut *tx)
            .await?;

        sqlx::query("INSERT INTO show (pk_show, str_name) VALUES ($1, $2)")
            .bind(show_id.to_string())
            .bind(format!("{}_show", prefix))
            .execute(&mut *tx)
            .await?;

        sqlx::query(
            "INSERT INTO folder (pk_folder, pk_show, pk_dept, str_name) VALUES ($1, $2, $3, $4)",
        )
        .bind(folder_id.to_string())
        .bind(show_id.to_string())
        .bind(dept_id.to_string())
        .bind(format!("{}_folder", prefix))
        .execute(&mut *tx)
        .await?;

        sqlx::query(
            "INSERT INTO job (pk_job, pk_folder, pk_show, pk_facility, pk_dept, str_name, \
             str_visible_name, str_shot, str_user, str_state) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        )
        .bind(job_id.to_string())
        .bind(folder_id.to_string())
        .bind(show_id.to_string())
        .bind(facility_id.to_string())
        .bind(dept_id.to_string())
        .bind(format!("{}_job", prefix))
        .bind(format!("{}_job", prefix))
        .bind(format!("{}_shot", prefix))
        .bind(format!("{}_user", prefix))
        .bind("PENDING")
        .execute(&mut *tx)
        .await?;

        // job_stat may already exist if a trigger created it on job insert (mirrors the harness).
        let job_stat_exists =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM job_stat WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(&mut *tx)
                .await?;
        if job_stat_exists == 0 {
            sqlx::query(
                "INSERT INTO job_stat (pk_job_stat, pk_job, int_waiting_count) VALUES ($1, $2, $3)",
            )
            .bind(Uuid::new_v4().to_string())
            .bind(job_id.to_string())
            .bind(1_i64)
            .execute(&mut *tx)
            .await?;
        }

        sqlx::query(
            "INSERT INTO layer (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, \
             str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        )
        .bind(layer_id.to_string())
        .bind(job_id.to_string())
        .bind(format!("{}_layer", prefix))
        .bind("echo 'compensation test frame'")
        .bind("1-1")
        .bind("general")
        .bind("PRE")
        .bind(100_i64)
        .bind(1_000_000_i64)
        .bind(0_i64)
        .bind(0_i64)
        .execute(&mut *tx)
        .await?;

        sqlx::query(
            "INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job, int_waiting_count, \
             int_total_count) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (pk_layer) DO NOTHING",
        )
        .bind(Uuid::new_v4().to_string())
        .bind(layer_id.to_string())
        .bind(job_id.to_string())
        .bind(1_i64)
        .bind(1_i64)
        .execute(&mut *tx)
        .await?;

        sqlx::query(
            "INSERT INTO frame (pk_frame, pk_layer, pk_job, str_name, str_state, int_number, \
             int_layer_order, int_dispatch_order) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        )
        .bind(frame_id.to_string())
        .bind(layer_id.to_string())
        .bind(job_id.to_string())
        .bind(format!("{}_frame", prefix))
        .bind("WAITING")
        .bind(1_i32)
        .bind(1_i32)
        .bind(1_i32)
        .execute(&mut *tx)
        .await?;

        tx.commit().await?;
        Ok((frame_id, prefix))
    }

    /// Best-effort teardown of everything seeded under `prefix`, triggers disabled so stat
    /// bookkeeping doesn't interfere with the deletes (mirrors `cleanup_test_data`).
    async fn cleanup(pool: &Pool<Postgres>, prefix: &str) {
        let like = format!("{}%", prefix);
        let mut tx = match pool.begin().await {
            Ok(tx) => tx,
            Err(_) => return,
        };
        let _ = sqlx::query("SET session_replication_role = 'replica'")
            .execute(&mut *tx)
            .await;
        for stmt in [
            "DELETE FROM frame WHERE str_name LIKE $1",
            "DELETE FROM layer_stat WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE $1)",
            "DELETE FROM layer_resource WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE $1)",
            "DELETE FROM layer WHERE str_name LIKE $1",
            "DELETE FROM job_stat WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE $1)",
            "DELETE FROM job_resource WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE $1)",
            "DELETE FROM job WHERE str_name LIKE $1",
            "DELETE FROM folder WHERE str_name LIKE $1",
            "DELETE FROM show WHERE str_name LIKE $1",
            "DELETE FROM facility WHERE str_name LIKE $1",
            "DELETE FROM dept WHERE str_name LIKE $1",
        ] {
            let _ = sqlx::query(stmt).bind(&like).execute(&mut *tx).await;
        }
        let _ = sqlx::query("SET session_replication_role = 'origin'")
            .execute(&mut *tx)
            .await;
        let _ = tx.commit().await;
    }

    /// Regression guard for Bug 2.
    ///
    /// A dispatch bumps `frame.int_version` V -> V+1 (`UPDATE_FRAME_STARTED`). Compensation's
    /// `clear_frame` guards on `int_version = $2`, so it must be called with the POST-dispatch
    /// version. The bug passed the stale pre-dispatch version, so the guard never matched and
    /// the frame stayed stuck in RUNNING forever. This pins both halves of the boundary.
    #[tokio::test]
    #[serial]
    async fn clear_frame_requires_post_dispatch_version() {
        let pool: Arc<Pool<Postgres>> = test_connection_pool().await.expect("connection pool");
        let (frame_id, prefix) = seed_one_waiting_frame(&pool).await.expect("seed frame");

        let pre_version: i32 =
            sqlx::query_scalar("SELECT int_version FROM frame WHERE pk_frame = $1")
                .bind(frame_id.to_string())
                .fetch_one(&*pool)
                .await
                .expect("frame version");

        // Transition WAITING -> RUNNING the way update_frame_started does (bumping int_version),
        // so the live DB version is now pre_version + 1.
        sqlx::query(
            "UPDATE frame SET str_state = 'RUNNING', str_host = $2, int_cores = 100, \
             ts_started = current_timestamp, int_version = int_version + 1 WHERE pk_frame = $1",
        )
        .bind(frame_id.to_string())
        .bind(format!("{}_host", prefix))
        .execute(&*pool)
        .await
        .expect("transition frame to RUNNING");
        let post_version = (pre_version + 1) as u32;

        let frame_dao = FrameDao::new().await.expect("frame dao");

        // Bug path: the stale pre-dispatch version must NOT clear the frame.
        let mut tx = pool.begin().await.expect("tx");
        let cleared_stale = frame_dao
            .clear_frame(&mut tx, &frame_id, pre_version as u32)
            .await
            .expect("clear_frame (stale version)");
        tx.commit().await.expect("commit");
        assert!(
            !cleared_stale,
            "clear_frame with the stale pre-dispatch version must return false"
        );
        let state_after_stale: String =
            sqlx::query_scalar("SELECT str_state FROM frame WHERE pk_frame = $1")
                .bind(frame_id.to_string())
                .fetch_one(&*pool)
                .await
                .expect("state after stale clear");
        assert_eq!(
            state_after_stale, "RUNNING",
            "frame must still be RUNNING after a stale-version clear"
        );

        // Fix path: the post-dispatch version clears the frame back to WAITING.
        let mut tx = pool.begin().await.expect("tx");
        let cleared_correct = frame_dao
            .clear_frame(&mut tx, &frame_id, post_version)
            .await
            .expect("clear_frame (post-dispatch version)");
        tx.commit().await.expect("commit");
        assert!(
            cleared_correct,
            "clear_frame with the post-dispatch version must return true"
        );
        let state_after_fix: String =
            sqlx::query_scalar("SELECT str_state FROM frame WHERE pk_frame = $1")
                .bind(frame_id.to_string())
                .fetch_one(&*pool)
                .await
                .expect("state after correct clear");
        assert_eq!(
            state_after_fix, "WAITING",
            "frame must be WAITING again after a post-dispatch-version clear"
        );

        cleanup(&pool, &prefix).await;
    }
}
