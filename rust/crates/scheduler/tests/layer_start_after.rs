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

//! Standalone integration test for the layer start-after gate (`layer.ts_start_after`).
//!
//! The reservation update (`UPDATE_FRAME_STARTED`) is the authoritative gate: it must refuse
//! to start a frame whose layer's start-after time is in the future, and allow it once the
//! gate is NULL or in the past. Self-contained on purpose - it seeds its own minimal
//! facility -> ... -> frame chain and does NOT depend on the cluster/Tag fixtures in
//! `smoke_tests.rs`. Gated behind the `smoke-tests` feature; requires the repo-root
//! `docker compose up -d flyway` Postgres (host `localhost:5432`, db/user `cuebot`).
//!
//! Run with: `cargo test -p scheduler --features smoke-tests --test layer_start_after`.

#[cfg(feature = "smoke-tests")]
mod util;

#[cfg(feature = "smoke-tests")]
mod layer_start_after {
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::time::SystemTime;

    use bytesize::ByteSize;
    use scheduler::dao::{FrameDao, FrameDaoError, LayerDao};
    use scheduler::models::{
        CoreSize, CoreSizeWithMultiplier, DispatchFrame, DispatchLayer, VirtualProc,
    };
    use serial_test::serial;
    use sqlx::{Pool, Postgres};
    use uuid::Uuid;

    use crate::util::test_connection_pool;

    /// Seeds a minimal facility -> dept -> show -> folder -> job -> layer -> frame chain with
    /// a single WAITING frame. Column lists and values mirror the `frame_dao_compensation`
    /// harness. Returns the frame id, layer id, job id and the unique row-name prefix used for
    /// cleanup.
    async fn seed_one_waiting_frame(
        pool: &Pool<Postgres>,
    ) -> Result<(Uuid, Uuid, Uuid, String), sqlx::Error> {
        let suffix = Uuid::new_v4().to_string()[..8].to_string();
        let prefix = format!("integ_test_startafter_{}", suffix);

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

        sqlx::query(
            "INSERT INTO layer (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, \
             str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        )
        .bind(layer_id.to_string())
        .bind(job_id.to_string())
        .bind(format!("{}_layer", prefix))
        .bind("echo 'start-after test frame'")
        .bind("1-1")
        .bind("general")
        .bind("PRE")
        .bind(100_i64)
        .bind(1_000_000_i64)
        .bind(0_i64)
        .bind(0_i64)
        .execute(&mut *tx)
        .await?;

        // The `after_insert_layer` trigger already created this row with zero counts, so the
        // conflict branch must overwrite them: the pending-frames query gates on
        // `layer_stat.int_waiting_count > 0` and would otherwise find nothing at all.
        sqlx::query(
            "INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job, int_waiting_count, \
             int_total_count) VALUES ($1, $2, $3, $4, $5) \
             ON CONFLICT (pk_layer) DO UPDATE SET \
             int_waiting_count = EXCLUDED.int_waiting_count, \
             int_total_count = EXCLUDED.int_total_count",
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
        Ok((frame_id, layer_id, job_id, prefix))
    }

    /// Total number of frames the pending-frames query surfaced across all layers.
    fn count_dispatch_frames(layers: &[DispatchLayer]) -> usize {
        layers.iter().map(|l| l.frames.len()).sum()
    }

    /// Best-effort teardown of everything seeded under `prefix`, triggers disabled so stat
    /// bookkeeping doesn't interfere with the deletes.
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

    /// Builds the minimal VirtualProc update_frame_started needs (host name, reserved
    /// resources, and the frame id/version driving the optimistic-lock guard).
    fn virtual_proc(
        frame_id: Uuid,
        layer_id: Uuid,
        frame_version: u32,
        prefix: &str,
    ) -> VirtualProc {
        VirtualProc {
            proc_id: Uuid::new_v4(),
            host_id: Uuid::new_v4(),
            show_id: Uuid::new_v4(),
            folder_id: Uuid::new_v4(),
            dept_id: Uuid::new_v4(),
            layer_id,
            job_id: Uuid::new_v4(),
            frame_id,
            alloc_id: Uuid::new_v4(),
            host_name: format!("{}_host", prefix),
            cores_reserved: CoreSizeWithMultiplier(100),
            memory_reserved: ByteSize::gb(1),
            gpus_reserved: 0,
            gpu_memory_reserved: ByteSize::b(0),
            os: "linux".to_string(),
            is_local_dispatch: false,
            frame: DispatchFrame {
                id: frame_id,
                frame_name: format!("{}_frame", prefix),
                show_id: Uuid::new_v4(),
                facility_id: Uuid::new_v4().to_string(),
                job_id: Uuid::new_v4(),
                layer_id,
                command: "echo 'start-after test frame'".to_string(),
                range: "1-1".to_string(),
                chunk_size: 1,
                show_name: format!("{}_show", prefix),
                shot: format!("{}_shot", prefix),
                user: format!("{}_user", prefix),
                uid: None,
                log_dir: "/tmp".to_string(),
                layer_name: format!("{}_layer", prefix),
                job_name: format!("{}_job", prefix),
                min_cores: CoreSize(1),
                layer_cores_limit: None,
                threadable: false,
                has_selfish_service: false,
                min_gpus: 0,
                min_gpu_memory: ByteSize::b(0),
                min_memory: ByteSize::gb(1),
                services: None,
                os: Some("linux".to_string()),
                loki_url: None,
                version: frame_version,
                updated_at: SystemTime::now(),
                env: HashMap::new(),
            },
        }
    }

    /// The reservation update must refuse a frame whose layer is delayed into the future and
    /// accept it once the gate has passed (or was cleared).
    #[tokio::test]
    #[serial]
    async fn update_frame_started_honours_layer_start_after() {
        let pool: Arc<Pool<Postgres>> = test_connection_pool().await.expect("connection pool");
        let (frame_id, layer_id, _job_id, prefix) =
            seed_one_waiting_frame(&pool).await.expect("seed frame");

        let version: i32 = sqlx::query_scalar("SELECT int_version FROM frame WHERE pk_frame = $1")
            .bind(frame_id.to_string())
            .fetch_one(&*pool)
            .await
            .expect("frame version");

        let frame_dao = FrameDao::new().await.expect("frame dao");
        let proc = virtual_proc(frame_id, layer_id, version as u32, &prefix);

        // Delay the layer: the reservation must be refused and the frame left WAITING.
        sqlx::query(
            "UPDATE layer SET ts_start_after = current_timestamp + interval '5 minutes', \
             str_start_after_reason = 'Automatic backoff: exit status 330' WHERE pk_layer = $1",
        )
        .bind(layer_id.to_string())
        .execute(&*pool)
        .await
        .expect("delay layer");

        let mut tx = pool.begin().await.expect("tx");
        let refused = frame_dao.update_frame_started(&mut tx, &proc).await;
        tx.commit().await.expect("commit");
        assert!(
            matches!(refused, Err(FrameDaoError::FrameCouldNotBeUpdated)),
            "update_frame_started must refuse a frame on a delayed layer, got {:?}",
            refused.map(|_| ()),
        );
        let state: String = sqlx::query_scalar("SELECT str_state FROM frame WHERE pk_frame = $1")
            .bind(frame_id.to_string())
            .fetch_one(&*pool)
            .await
            .expect("frame state");
        assert_eq!(state, "WAITING", "refused frame must stay WAITING");

        // Move the gate into the past: the same reservation now succeeds.
        sqlx::query(
            "UPDATE layer SET ts_start_after = current_timestamp - interval '1 minute' \
             WHERE pk_layer = $1",
        )
        .bind(layer_id.to_string())
        .execute(&*pool)
        .await
        .expect("expire layer delay");

        let mut tx = pool.begin().await.expect("tx");
        let started = frame_dao
            .update_frame_started(&mut tx, &proc)
            .await
            .expect("update_frame_started after the gate passed");
        tx.commit().await.expect("commit");
        assert_eq!(started, (version + 1) as u32, "version bumps on start");
        let state: String = sqlx::query_scalar("SELECT str_state FROM frame WHERE pk_frame = $1")
            .bind(frame_id.to_string())
            .fetch_one(&*pool)
            .await
            .expect("frame state");
        assert_eq!(state, "RUNNING", "frame must start once the gate is past");

        cleanup(&pool, &prefix).await;
    }

    /// The pending-frames query (`QUERY_LAYERS_WITH_FRAMES` in `layer_dao.rs`) is the advisory
    /// half of the gate: a layer delayed into the future must surface no frames, and must
    /// surface them again once the gate has passed. Cheap to get wrong silently, since the
    /// authoritative reservation gate would still hold the line.
    #[tokio::test]
    #[serial]
    async fn pending_frames_query_skips_delayed_layer() {
        let pool: Arc<Pool<Postgres>> = test_connection_pool().await.expect("connection pool");
        let (_frame_id, layer_id, job_id, prefix) =
            seed_one_waiting_frame(&pool).await.expect("seed frame");

        let layer_dao = LayerDao::new().await.expect("layer dao");
        // Matches `str_tags` on the seeded layer; the query intersects this list with the
        // layer's tags.
        let tags = vec!["general".to_string()];

        // Bookable while the gate is unset.
        let layers = layer_dao
            .query_layers(job_id, tags.clone())
            .await
            .expect("query_layers failed");
        assert!(
            count_dispatch_frames(&layers) > 0,
            "Expected frames while the layer has no start-after gate"
        );

        // Delay the layer: the query must return nothing for it.
        sqlx::query(
            "UPDATE layer SET ts_start_after = current_timestamp + interval '5 minutes', \
             str_start_after_reason = 'Automatic backoff: exit status 330' WHERE pk_layer = $1",
        )
        .bind(layer_id.to_string())
        .execute(&*pool)
        .await
        .expect("delay layer");

        let layers = layer_dao
            .query_layers(job_id, tags.clone())
            .await
            .expect("query_layers failed");
        assert_eq!(
            count_dispatch_frames(&layers),
            0,
            "Expected no frames while the layer's start-after gate is in the future"
        );

        // Expire the gate: frames surface again.
        sqlx::query(
            "UPDATE layer SET ts_start_after = current_timestamp - interval '1 minute' \
             WHERE pk_layer = $1",
        )
        .bind(layer_id.to_string())
        .execute(&*pool)
        .await
        .expect("expire layer delay");

        let layers = layer_dao
            .query_layers(job_id, tags)
            .await
            .expect("query_layers failed");
        assert!(
            count_dispatch_frames(&layers) > 0,
            "Expected frames again once the start-after gate is in the past"
        );

        cleanup(&pool, &prefix).await;
    }
}
