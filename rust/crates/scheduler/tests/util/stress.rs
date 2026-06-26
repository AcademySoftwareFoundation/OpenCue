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

//! Support machinery for the booking + accounting stress suite
//! (`tests/stress_tests.rs`):
//!
//! - [`create_stress_config`]: scheduler config tuned so a test run terminates on
//!   its own and the Redis hot path is the accounting system under test
//!   (reconciliation loops pushed out beyond the test horizon).
//! - [`seed_farm`]: deterministic bulk seeding of a complete farm (facility →
//!   show/allocs/subscriptions → hosts/tags → jobs/layers/frames) using multi-row
//!   inserts so tens of thousands of frames seed in seconds.
//! - [`spawn_stall_watchdog`]: external termination control. A saturated farm never
//!   drains, so `pipeline::run` would loop forever; the watchdog pauses the phase's
//!   jobs once bookings stop growing, which lets the feed quit gracefully via
//!   `empty_job_cycles_before_quiting`.
//! - [`audit_accounting`]: cross-checks every Redis `acct:*` hash touched by the
//!   show against `SUM(proc)` in Postgres (the canonical record), plus host/frame/
//!   stat invariants and cap enforcement (subscription burst, job max-cores).
//! - [`clean_up_stress_data`] / [`residue_counts`]: removes everything matching the
//!   stress prefix and proves it's gone.

#![allow(dead_code)]

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use chrono::{DateTime, Utc};
use rand::{rngs::StdRng, seq::SliceRandom, Rng, SeedableRng};
use scheduler::{
    accounting::accounting_service,
    cluster::Cluster,
    cluster_key::{Tag, TagType},
    config::{
        AccountingConfig, Config, DatabaseConfig, HostBookingStrategy, HostCacheConfig,
        LoggingConfig, QueueConfig, RqdConfig, SchedulerConfig, StreamConfig,
    },
};
use sqlx::{Pool, Postgres, QueryBuilder};
use tokio::task::JoinHandle;
use tracing::info;
use uuid::Uuid;

use super::{TEST_DB_HOST, TEST_DB_NAME, TEST_DB_PASSWORD, TEST_DB_PORT, TEST_DB_USER};

/// Centicore multiplier used across the OpenCue schema (`int_cores*` columns).
pub const CORE_MULT: i64 = 100;

const SEED: u64 = 0x0C0FFEE;

// =============================================================================
// Config
// =============================================================================

/// Config for stress runs. Differences from production defaults that matter here:
///
/// - `empty_job_cycles_before_quiting` + short cluster sleeps: `pipeline::run`
///   exits a few seconds after every cluster stops yielding jobs (either because
///   the workload drained or because the watchdog paused it).
/// - `recompute_interval` / `limit_reseed_interval` = 1h: the reconciliation loops
///   never fire inside the test window, so the final store state is the product of
///   the dispatch hot path alone — exactly what the audit wants to verify.
/// - `host_staleness_threshold` = 1h: seeded hosts never report a fresh `ts_ping`
///   (no RQD), so the cache must not evict them mid-run.
/// - `dry_run_mode` = true: full booking path (in-memory check+increment + proc insert
///   + host decrement + frame start) without gRPC calls to RQD.
pub fn create_stress_config() -> Config {
    Config {
        logging: LoggingConfig {
            level: "info".to_string(),
            path: "/tmp/scheduler_stress_test.log".to_string(),
            file_appender: false,
        },
        queue: QueueConfig {
            monitor_interval: Duration::from_secs(5),
            worker_threads: 4,
            dispatch_frames_per_layer_limit: 50,
            core_multiplier: CORE_MULT as u32,
            memory_stranded_threshold: bytesize::ByteSize::mb(100),
            job_back_off_duration: Duration::from_secs(2),
            cluster_empty_sleep: Duration::from_secs(2),
            cluster_reload_interval: Duration::from_secs(3600),
            // Push the awake-rescan past the test horizon like the other
            // reconciliation loops: build()'s initial scan seeds the awake set
            // from the fully-seeded farm, and it then stays put for the run so
            // the benchmark timing isn't perturbed by re-gating.
            active_scan_interval: Duration::from_secs(3600),
            cluster_saturated_sleep: Duration::from_millis(500),
            stream: StreamConfig {
                cluster_buffer_size: 4,
                job_buffer_size: 16,
            },
            max_jobs_per_cluster_pass: 50,
            manual_tags_chunk_size: 10,
            hostname_tags_chunk_size: 20,
            host_candidate_attempts_per_layer: 5,
            empty_job_cycles_before_quiting: Some(10),
            mem_reserved_min: bytesize::ByteSize::mb(250),
            selfish_services: Vec::new(),
            host_booking_strategy: HostBookingStrategy::Saturation {
                core_saturation: true,
                memory_saturation: false,
            },
            frame_memory_soft_limit: 1.6,
            frame_memory_hard_limit: 2.0,
            metrics_port: 9091,
        },
        database: DatabaseConfig {
            pool_size: 32,
            core_multiplier: CORE_MULT as u32,
            db_host: TEST_DB_HOST.to_string(),
            db_name: TEST_DB_NAME.to_string(),
            db_user: TEST_DB_USER.to_string(),
            db_pass: TEST_DB_PASSWORD.to_string(),
            db_port: TEST_DB_PORT,
        },
        rqd: RqdConfig {
            grpc_port: 8444,
            dry_run_mode: true,
        },
        host_cache: HostCacheConfig {
            update_stat_on_book: true,
            host_staleness_threshold: Duration::from_secs(3600),
            ..Default::default()
        },
        scheduler: SchedulerConfig::default(),
        accounting: AccountingConfig {
            recompute_interval: Duration::from_secs(3600),
            limit_reseed_interval: Duration::from_secs(3600),
            managed_shows_ttl: Duration::from_secs(5),
        },
        sentry_dsn: None,
    }
}

// =============================================================================
// Farm spec + seeding
// =============================================================================

/// Shape of one self-contained dataset (show + allocs + hosts + jobs).
/// All core quantities are whole cores; conversion to centicores happens at
/// insert time.
#[derive(Debug, Clone)]
pub struct FarmSpec {
    /// Unique name prefix; must start with `stress_` so sweep cleanup finds it.
    /// Keep it short (≤ 16 chars): `alloc.str_tag` is VARCHAR(24) and
    /// `host.str_name` is VARCHAR(30), and both get `{prefix}_…` names.
    pub prefix: String,
    pub alloc_count: usize,
    pub host_count: usize,
    /// Host core counts are drawn from this list (whole cores).
    pub host_cores_choices: Vec<i64>,
    /// Host memory drawn uniformly from this range (GB).
    pub host_mem_gb_range: (u64, u64),
    /// Per-(show, alloc) subscription size, whole cores.
    pub sub_size_cores: i64,
    /// Per-(show, alloc) subscription burst, whole cores. This is the cap the
    /// Redis Lua enforces on the hot path.
    pub sub_burst_cores: i64,
    pub manual_tag_count: usize,
    pub job_count: usize,
    pub layers_per_job: usize,
    pub frames_per_layer: usize,
    /// Layer `int_cores_min` drawn from this list (whole cores).
    pub layer_cores_choices: Vec<i64>,
    /// Layer `int_mem_min` drawn uniformly from this range (GB).
    pub layer_mem_gb_range: (u64, u64),
    /// `job_resource.int_max_cores` in whole cores. Must be > 0: the `vs_waiting`
    /// view only surfaces shows where `int_max_cores - int_cores >= 100`
    /// centicores, so 0 silently makes every job unbookable. Use a huge value
    /// for "effectively unlimited".
    pub job_max_cores: i64,
}

impl FarmSpec {
    pub fn total_frames(&self) -> usize {
        self.job_count * self.layers_per_job * self.frames_per_layer
    }
}

/// Handle to a seeded dataset.
#[derive(Debug)]
pub struct StressFarm {
    pub prefix: String,
    pub show_id: Uuid,
    pub facility_id: Uuid,
    pub dept_id: Uuid,
    pub folder_id: Uuid,
    /// (alloc_id, alloc/tag name)
    pub allocs: Vec<(Uuid, String)>,
    pub clusters: Vec<Cluster>,
    pub spec: FarmSpec,
}

/// Seeds a complete farm in bulk. Deterministic for a given spec (fixed RNG seed),
/// so consecutive benchmark runs at the same scale book the same workload.
pub async fn seed_farm(pool: &Pool<Postgres>, spec: FarmSpec) -> Result<StressFarm, sqlx::Error> {
    let prefix = spec.prefix.clone();
    let facility_id = Uuid::new_v4();
    let dept_id = Uuid::new_v4();
    let show_id = Uuid::new_v4();
    let folder_id = Uuid::new_v4();
    let mut rng = StdRng::seed_from_u64(SEED);

    let mut tx = pool.begin().await?;

    sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
        .bind(facility_id.to_string())
        .bind(format!("{prefix}_facility"))
        .execute(&mut *tx)
        .await?;
    sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
        .bind(dept_id.to_string())
        .bind(format!("{prefix}_dept"))
        .execute(&mut *tx)
        .await?;
    // b_scheduler_managed = true puts the show under Rust-scheduler accounting:
    // apply_booking writes the acct:* hashes and the audit below has teeth.
    sqlx::query("INSERT INTO show (pk_show, str_name, b_scheduler_managed) VALUES ($1, $2, true)")
        .bind(show_id.to_string())
        .bind(format!("{prefix}_show"))
        .execute(&mut *tx)
        .await?;
    sqlx::query(
        "INSERT INTO folder (pk_folder, pk_show, pk_dept, str_name) VALUES ($1, $2, $3, $4)",
    )
    .bind(folder_id.to_string())
    .bind(show_id.to_string())
    .bind(dept_id.to_string())
    .bind(format!("{prefix}_folder"))
    .execute(&mut *tx)
    .await?;
    // The pending-job query INNER JOINs folder_resource; without this row no job
    // in the folder is ever bookable. Column defaults give -1 (unlimited) caps.
    sqlx::query(
        "INSERT INTO folder_resource (pk_folder_resource, pk_folder) VALUES ($1, $2) \
         ON CONFLICT DO NOTHING",
    )
    .bind(Uuid::new_v4().to_string())
    .bind(folder_id.to_string())
    .execute(&mut *tx)
    .await?;

    let mut allocs: Vec<(Uuid, String)> = Vec::with_capacity(spec.alloc_count);
    for i in 0..spec.alloc_count {
        let alloc_id = Uuid::new_v4();
        // Short suffix: alloc.str_tag is VARCHAR(24), so the whole name must fit.
        let name = format!("{prefix}_a{i}");
        sqlx::query(
            "INSERT INTO alloc (pk_alloc, str_name, pk_facility, str_tag) VALUES ($1, $2, $3, $4)",
        )
        .bind(alloc_id.to_string())
        .bind(&name)
        .bind(facility_id.to_string())
        .bind(&name)
        .execute(&mut *tx)
        .await?;
        sqlx::query(
            "INSERT INTO subscription (pk_subscription, pk_alloc, pk_show, int_size, int_burst) \
             VALUES ($1, $2, $3, $4, $5)",
        )
        .bind(Uuid::new_v4().to_string())
        .bind(alloc_id.to_string())
        .bind(show_id.to_string())
        .bind(spec.sub_size_cores * CORE_MULT)
        .bind(spec.sub_burst_cores * CORE_MULT)
        .execute(&mut *tx)
        .await?;
        allocs.push((alloc_id, name));
    }

    // Manual tags, chunked into clusters of roughly 4 groups, plus one Alloc
    // cluster per allocation - mirrors how ClusterFeed::load_all shapes the feed.
    let manual_tags: Vec<String> = (0..spec.manual_tag_count)
        .map(|i| format!("{prefix}_t{i}"))
        .collect();
    let mut clusters = Vec::new();
    if !manual_tags.is_empty() {
        let chunk_size = manual_tags.len().div_ceil(4).max(1);
        for chunk in manual_tags.chunks(chunk_size) {
            clusters.push(Cluster::multiple_tag(
                facility_id.to_string(),
                show_id,
                chunk
                    .iter()
                    .map(|name| Tag {
                        name: name.clone(),
                        ttype: TagType::Manual,
                        alloc_id: None,
                    })
                    .collect(),
            ));
        }
    }
    for (alloc_id, alloc_name) in &allocs {
        clusters.push(Cluster::single_tag(
            facility_id.to_string(),
            show_id,
            Tag {
                name: alloc_name.clone(),
                ttype: TagType::Alloc,
                alloc_id: Some(*alloc_id),
            },
        ));
    }

    // --- Hosts (bulk) ---
    struct HostRow {
        id: String,
        alloc: String,
        name: String,
        cores_centi: i64,
        mem_kb: i64,
        tags: Vec<(String, &'static str)>,
    }
    let mut host_rows = Vec::with_capacity(spec.host_count);
    for i in 0..spec.host_count {
        let (alloc_id, alloc_name) = &allocs[i % allocs.len()];
        let cores = *spec.host_cores_choices.choose(&mut rng).unwrap();
        let mem_gb = rng.gen_range(spec.host_mem_gb_range.0..=spec.host_mem_gb_range.1);
        let mut tags: Vec<(String, &'static str)> = vec![(alloc_name.clone(), "ALLOC")];
        if !manual_tags.is_empty() {
            if i < manual_tags.len() {
                // Guarantee every manual tag lands on at least one host.
                tags.push((manual_tags[i].clone(), "MANUAL"));
            } else {
                let n_tags = rng.gen_range(0..=2);
                for tag in manual_tags.choose_multiple(&mut rng, n_tags) {
                    tags.push((tag.clone(), "MANUAL"));
                }
            }
        }
        host_rows.push(HostRow {
            id: Uuid::new_v4().to_string(),
            alloc: alloc_id.to_string(),
            // host.str_name is VARCHAR(30); keep the suffix short.
            name: format!("{prefix}_h{i}"),
            cores_centi: cores * CORE_MULT,
            mem_kb: (mem_gb * 1024 * 1024) as i64,
            tags,
        });
    }

    for chunk in host_rows.chunks(500) {
        let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
            "INSERT INTO host (pk_host, pk_alloc, str_name, str_lock_state, int_cores, \
             int_cores_idle, int_mem, int_mem_idle, int_gpus, int_gpus_idle, int_gpu_mem, \
             int_gpu_mem_idle, int_thread_mode) ",
        );
        qb.push_values(chunk, |mut b, h| {
            b.push_bind(&h.id)
                .push_bind(&h.alloc)
                .push_bind(&h.name)
                .push_bind("OPEN")
                .push_bind(h.cores_centi)
                .push_bind(h.cores_centi)
                .push_bind(h.mem_kb)
                .push_bind(h.mem_kb)
                .push_bind(0i64)
                .push_bind(0i64)
                .push_bind(0i64)
                .push_bind(0i64)
                .push_bind(0i32);
        });
        qb.build().execute(&mut *tx).await?;

        let now = Utc::now();
        let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
            "INSERT INTO host_stat (pk_host_stat, pk_host, str_state, str_os, int_mem_total, \
             int_mem_free, int_gpu_mem_total, int_gpu_mem_free, ts_ping) ",
        );
        qb.push_values(chunk, |mut b, h| {
            b.push_bind(Uuid::new_v4().to_string())
                .push_bind(&h.id)
                .push_bind("UP")
                .push_bind("linux")
                .push_bind(h.mem_kb)
                .push_bind(h.mem_kb)
                .push_bind(0i64)
                .push_bind(0i64)
                .push_bind(now);
        });
        qb.build().execute(&mut *tx).await?;

        let tag_rows: Vec<(&String, &(String, &'static str))> = chunk
            .iter()
            .flat_map(|h| h.tags.iter().map(move |t| (&h.id, t)))
            .collect();
        for tag_chunk in tag_rows.chunks(2000) {
            let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
                "INSERT INTO host_tag (pk_host_tag, pk_host, str_tag, str_tag_type) ",
            );
            qb.push_values(tag_chunk, |mut b, (host_id, (tag, ttype))| {
                b.push_bind(Uuid::new_v4().to_string())
                    .push_bind(host_id.as_str())
                    .push_bind(tag)
                    .push_bind(*ttype);
            });
            qb.build().execute(&mut *tx).await?;
        }
    }

    // --- Jobs / layers / frames (bulk) ---
    // Layers tag themselves with 1-3 names drawn from the union of manual tags and
    // alloc tags, so work spreads across every cluster in the feed.
    let all_layer_tags: Vec<String> = manual_tags
        .iter()
        .cloned()
        .chain(allocs.iter().map(|(_, name)| name.clone()))
        .collect();

    struct JobRow {
        id: String,
        name: String,
    }
    struct LayerRow {
        id: String,
        job: String,
        name: String,
        tags: String,
        cores_centi: i64,
        mem_kb: i64,
    }
    let mut job_rows = Vec::with_capacity(spec.job_count);
    let mut layer_rows = Vec::with_capacity(spec.job_count * spec.layers_per_job);
    for j in 0..spec.job_count {
        let job_id = Uuid::new_v4().to_string();
        for l in 0..spec.layers_per_job {
            let n_tags = rng.gen_range(1..=3.min(all_layer_tags.len()));
            let tags: Vec<String> = all_layer_tags
                .choose_multiple(&mut rng, n_tags)
                .cloned()
                .collect();
            let cores = *spec.layer_cores_choices.choose(&mut rng).unwrap();
            let mem_gb = rng.gen_range(spec.layer_mem_gb_range.0..=spec.layer_mem_gb_range.1);
            layer_rows.push(LayerRow {
                id: Uuid::new_v4().to_string(),
                job: job_id.clone(),
                name: format!("{prefix}_j{j}_l{l}"),
                tags: tags.join(" | "),
                cores_centi: cores * CORE_MULT,
                mem_kb: (mem_gb * 1024 * 1024) as i64,
            });
        }
        job_rows.push(JobRow {
            id: job_id,
            name: format!("{prefix}_j{j}"),
        });
    }

    for chunk in job_rows.chunks(500) {
        let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
            "INSERT INTO job (pk_job, pk_folder, pk_show, pk_facility, pk_dept, str_name, \
             str_visible_name, str_shot, str_user, str_state, str_os) ",
        );
        qb.push_values(chunk, |mut b, j| {
            b.push_bind(&j.id)
                .push_bind(folder_id.to_string())
                .push_bind(show_id.to_string())
                .push_bind(facility_id.to_string())
                .push_bind(dept_id.to_string())
                .push_bind(&j.name)
                .push_bind(&j.name)
                .push_bind("stress_shot")
                .push_bind("stress_user")
                .push_bind("PENDING")
                .push_bind("linux");
        });
        qb.build().execute(&mut *tx).await?;
    }

    for chunk in layer_rows.chunks(500) {
        let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
            "INSERT INTO layer (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, \
             str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) ",
        );
        qb.push_values(chunk, |mut b, l| {
            b.push_bind(&l.id)
                .push_bind(&l.job)
                .push_bind(&l.name)
                .push_bind("echo stress")
                .push_bind(format!("1-{}", spec.frames_per_layer))
                .push_bind(&l.tags)
                .push_bind("PRE")
                .push_bind(l.cores_centi)
                .push_bind(l.mem_kb)
                .push_bind(0i64)
                .push_bind(0i64);
        });
        qb.build().execute(&mut *tx).await?;
    }

    struct FrameRow<'a> {
        layer: &'a str,
        job: &'a str,
        name: String,
        number: i32,
    }
    let frame_rows: Vec<FrameRow> = layer_rows
        .iter()
        .flat_map(|l| {
            (1..=spec.frames_per_layer as i32).map(move |n| FrameRow {
                layer: &l.id,
                job: &l.job,
                name: format!("{:04}-{}", n, l.name),
                number: n,
            })
        })
        .collect();
    let now = Utc::now();
    for chunk in frame_rows.chunks(1000) {
        let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
            "INSERT INTO frame (pk_frame, pk_layer, pk_job, str_name, str_state, int_number, \
             int_layer_order, int_dispatch_order, ts_updated) ",
        );
        qb.push_values(chunk, |mut b, f| {
            b.push_bind(Uuid::new_v4().to_string())
                .push_bind(f.layer)
                .push_bind(f.job)
                .push_bind(&f.name)
                .push_bind("WAITING")
                .push_bind(f.number)
                .push_bind(f.number)
                .push_bind(f.number)
                .push_bind(now);
        });
        qb.build().execute(&mut *tx).await?;
    }

    // --- Stat / resource rows (set-based; tolerate trigger-created rows) ---
    let like = format!("{prefix}%");
    let waiting_per_job = (spec.layers_per_job * spec.frames_per_layer) as i64;
    let waiting_per_layer = spec.frames_per_layer as i64;
    let job_max_cores_centi = spec.job_max_cores * CORE_MULT;

    sqlx::query(
        "INSERT INTO job_stat (pk_job_stat, pk_job, int_waiting_count) \
         SELECT gen_random_uuid()::varchar, j.pk_job, $2 FROM job j \
         WHERE j.str_name LIKE $1 \
           AND NOT EXISTS (SELECT 1 FROM job_stat js WHERE js.pk_job = j.pk_job)",
    )
    .bind(&like)
    .bind(waiting_per_job)
    .execute(&mut *tx)
    .await?;
    sqlx::query(
        "UPDATE job_stat js SET int_waiting_count = $2 \
         FROM job j WHERE j.pk_job = js.pk_job AND j.str_name LIKE $1",
    )
    .bind(&like)
    .bind(waiting_per_job)
    .execute(&mut *tx)
    .await?;

    // Deterministic pseudo-random priorities so the feed exercises the strict
    // ORDER BY priority path with a realistic spread.
    sqlx::query(
        "INSERT INTO job_resource \
         (pk_job_resource, pk_job, int_priority, int_max_cores, int_max_gpus) \
         SELECT gen_random_uuid()::varchar, j.pk_job, \
                (abs(hashtext(j.pk_job)) % 200) + 1, $2, 0 \
         FROM job j WHERE j.str_name LIKE $1 \
           AND NOT EXISTS (SELECT 1 FROM job_resource jr WHERE jr.pk_job = j.pk_job)",
    )
    .bind(&like)
    .bind(job_max_cores_centi)
    .execute(&mut *tx)
    .await?;
    sqlx::query(
        "UPDATE job_resource jr \
         SET int_priority = (abs(hashtext(j.pk_job)) % 200) + 1, \
             int_max_cores = $2, int_max_gpus = 0 \
         FROM job j WHERE j.pk_job = jr.pk_job AND j.str_name LIKE $1",
    )
    .bind(&like)
    .bind(job_max_cores_centi)
    .execute(&mut *tx)
    .await?;

    sqlx::query(
        "INSERT INTO layer_stat \
         (pk_layer_stat, pk_layer, pk_job, int_waiting_count, int_total_count) \
         SELECT gen_random_uuid()::varchar, l.pk_layer, l.pk_job, $2, $2 \
         FROM layer l JOIN job j ON j.pk_job = l.pk_job \
         WHERE j.str_name LIKE $1 \
           AND NOT EXISTS (SELECT 1 FROM layer_stat ls WHERE ls.pk_layer = l.pk_layer)",
    )
    .bind(&like)
    .bind(waiting_per_layer)
    .execute(&mut *tx)
    .await?;
    sqlx::query(
        "UPDATE layer_stat ls SET int_waiting_count = $2, int_total_count = $2 \
         FROM layer l JOIN job j ON j.pk_job = l.pk_job \
         WHERE ls.pk_layer = l.pk_layer AND j.str_name LIKE $1",
    )
    .bind(&like)
    .bind(waiting_per_layer)
    .execute(&mut *tx)
    .await?;

    sqlx::query(
        "INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) \
         SELECT gen_random_uuid()::varchar, l.pk_layer, l.pk_job \
         FROM layer l JOIN job j ON j.pk_job = l.pk_job \
         WHERE j.str_name LIKE $1 \
           AND NOT EXISTS (SELECT 1 FROM layer_resource lr WHERE lr.pk_layer = l.pk_layer)",
    )
    .bind(&like)
    .execute(&mut *tx)
    .await?;

    tx.commit().await?;

    info!(
        "Seeded farm '{}': {} hosts, {} jobs x {} layers x {} frames = {} frames",
        prefix,
        spec.host_count,
        spec.job_count,
        spec.layers_per_job,
        spec.frames_per_layer,
        spec.total_frames()
    );

    Ok(StressFarm {
        prefix,
        show_id,
        facility_id,
        dept_id,
        folder_id,
        allocs,
        clusters,
        spec,
    })
}

// =============================================================================
// Watchdog
// =============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WatchdogOutcome {
    /// Booking stopped growing for the stall window; jobs were paused.
    Stalled,
    /// The hard timeout elapsed; jobs were paused.
    TimedOut,
}

/// Monitors `proc` growth for the prefix and pauses the prefix's jobs once
/// bookings stop progressing (`stall`) or at `hard_timeout`, whichever first.
/// Pausing makes the pending-job query return nothing, which lets the feed quit
/// via `empty_job_cycles_before_quiting` — the graceful, externally-observable
/// way to stop `pipeline::run` against a workload that can never fully drain.
pub fn spawn_stall_watchdog(
    pool: Arc<Pool<Postgres>>,
    prefix: String,
    stall: Duration,
    hard_timeout: Duration,
) -> JoinHandle<WatchdogOutcome> {
    tokio::spawn(async move {
        let like = format!("{prefix}%");
        let started = tokio::time::Instant::now();
        let mut last_count: i64 = -1;
        let mut last_growth = tokio::time::Instant::now();
        loop {
            tokio::time::sleep(Duration::from_secs(2)).await;
            let count: i64 = sqlx::query_scalar(
                "SELECT count(*) FROM proc p JOIN job j ON j.pk_job = p.pk_job \
                 WHERE j.str_name LIKE $1",
            )
            .bind(&like)
            .fetch_one(&*pool)
            .await
            .unwrap_or(last_count);

            if count > last_count {
                last_count = count;
                last_growth = tokio::time::Instant::now();
            }

            let timed_out = started.elapsed() >= hard_timeout;
            let stalled = last_growth.elapsed() >= stall;
            if timed_out || stalled {
                let paused = sqlx::query(
                    "UPDATE job SET b_paused = true \
                     WHERE str_name LIKE $1 AND str_state = 'PENDING' AND b_paused = false",
                )
                .bind(&like)
                .execute(&*pool)
                .await
                .map(|r| r.rows_affected())
                .unwrap_or(0);
                info!(
                    "Watchdog for '{}': {} after {:?} ({} procs booked) - paused {} jobs",
                    prefix,
                    if timed_out { "hard timeout" } else { "stall" },
                    started.elapsed(),
                    last_count.max(0),
                    paused
                );
                return if timed_out {
                    WatchdogOutcome::TimedOut
                } else {
                    WatchdogOutcome::Stalled
                };
            }
        }
    })
}

// =============================================================================
// Accounting audit
// =============================================================================

#[derive(Debug)]
pub struct SubUsage {
    pub alloc_name: String,
    pub booked_cores: i64,
    pub burst_cores: i64,
}

#[derive(Debug, Default)]
pub struct AuditOutcome {
    /// Human-readable invariant violations. Empty = accounting is consistent.
    pub violations: Vec<String>,
    /// Procs booked for the farm's show.
    pub dispatched_procs: i64,
    /// Total booked cores across the show (from PG `proc`).
    pub booked_cores: i64,
    pub per_sub: Vec<SubUsage>,
}

/// Compare one vertex's expected centicores/gpus against the store's booked `(cores, gpus)`.
fn cmp_vertex(label: &str, want_centi: i64, want_gpus: i64, got: (i64, i64)) -> Vec<String> {
    let want_cores = want_centi / CORE_MULT;
    let mut v = Vec::new();
    if got.0 != want_cores {
        v.push(format!(
            "{label}: store cores={} but SUM(proc) says {want_cores}",
            got.0
        ));
    }
    if got.1 != want_gpus {
        v.push(format!(
            "{label}: store gpus={} but SUM(proc) says {want_gpus}",
            got.1
        ));
    }
    v
}

/// Cross-checks the in-memory accounting store against `SUM(proc)` in Postgres (the
/// canonical record of bookings), and validates the cap + host/frame/stat invariants
/// that booking must preserve:
///
/// 1. Every subscription/folder/job booked counter in the store holds exactly
///    `SUM(proc.int_cores_reserved)/100` cores and `SUM(proc.int_gpus_reserved)` GPUs for
///    its grouping. With the recompute loop pushed past the test window, agreement here
///    proves the *hot path* (book + rollback) kept the store exact on its own. Layer and
///    point are not tracked (the booking check never reads them).
/// 2. Jobs with no bookings have no leaked store counters.
/// 3. Per-(show, alloc) booked cores never exceed the subscription burst.
/// 4. Per-job booked cores never exceed `job_resource.int_max_cores` (when set).
/// 5. Host ledger: `int_cores - int_cores_idle == SUM(proc)` per host, never negative.
/// 6. Frame/proc agreement: one RUNNING frame per proc.
/// 7. Trigger-maintained `job_stat.int_waiting_count` matches the frame table.
pub async fn audit_accounting(pool: &Pool<Postgres>, farm: &StressFarm) -> AuditOutcome {
    let mut out = AuditOutcome::default();
    let show = farm.show_id.to_string();
    let show_id = farm.show_id;
    let like = format!("{}%", farm.prefix);

    // --- 1. + 2.: store counters vs SUM(proc), grouped by the enforced vertices ---
    #[derive(sqlx::FromRow)]
    struct BookedRow {
        pk_alloc: String,
        pk_folder: String,
        pk_job: String,
        cores: i64,
        gpus: i64,
    }
    let rows: Vec<BookedRow> = sqlx::query_as(
        "SELECT h.pk_alloc, j.pk_folder, p.pk_job, \
                COALESCE(SUM(p.int_cores_reserved), 0)::bigint AS cores, \
                COALESCE(SUM(p.int_gpus_reserved), 0)::bigint AS gpus \
         FROM proc p \
         JOIN host h ON h.pk_host = p.pk_host \
         JOIN job  j ON j.pk_job = p.pk_job \
         WHERE j.pk_show = $1 AND p.b_local = false \
         GROUP BY h.pk_alloc, j.pk_folder, p.pk_job",
    )
    .bind(&show)
    .fetch_all(pool)
    .await
    .expect("booked snapshot query");

    // Aggregate centicores per vertex key (mirrors the recompute aggregation).
    let mut exp_sub: HashMap<(Uuid, Uuid), (i64, i64)> = HashMap::new();
    let mut exp_folder: HashMap<Uuid, (i64, i64)> = HashMap::new();
    let mut exp_job: HashMap<Uuid, (i64, i64)> = HashMap::new();
    for r in &rows {
        let alloc = Uuid::parse_str(&r.pk_alloc).expect("alloc uuid");
        let folder = Uuid::parse_str(&r.pk_folder).expect("folder uuid");
        let job = Uuid::parse_str(&r.pk_job).expect("job uuid");
        let s = exp_sub.entry((show_id, alloc)).or_insert((0, 0));
        s.0 += r.cores;
        s.1 += r.gpus;
        let f = exp_folder.entry(folder).or_insert((0, 0));
        f.0 += r.cores;
        f.1 += r.gpus;
        let j = exp_job.entry(job).or_insert((0, 0));
        j.0 += r.cores;
        j.1 += r.gpus;
    }

    // The store is the live accounting state used by the pipeline we just ran.
    let store = accounting_service()
        .await
        .expect("accounting service")
        .store()
        .audit_snapshot();

    for (&(s, a), &(c, g)) in &exp_sub {
        out.violations.extend(cmp_vertex(
            &format!("sub:{s}:{a}"),
            c,
            g,
            store.sub.get(&(s, a)).copied().unwrap_or((0, 0)),
        ));
    }
    for (&f, &(c, g)) in &exp_folder {
        out.violations.extend(cmp_vertex(
            &format!("folder:{f}"),
            c,
            g,
            store.folder.get(&f).copied().unwrap_or((0, 0)),
        ));
    }
    for (&jb, &(c, g)) in &exp_job {
        out.violations.extend(cmp_vertex(
            &format!("job:{jb}"),
            c,
            g,
            store.job.get(&jb).copied().unwrap_or((0, 0)),
        ));
    }

    // 2. Jobs with no procs must not have leaked a non-zero store counter.
    let all_jobs: Vec<String> = sqlx::query_scalar("SELECT pk_job FROM job WHERE pk_show = $1")
        .bind(&show)
        .fetch_all(pool)
        .await
        .expect("job list query");
    for job in &all_jobs {
        let job_id = Uuid::parse_str(job).expect("job uuid");
        if !exp_job.contains_key(&job_id) {
            let got = store.job.get(&job_id).map(|(c, _)| *c).unwrap_or(0);
            if got != 0 {
                out.violations.push(format!(
                    "job:{job}: store cores={got} leaked for a job with no procs"
                ));
            }
        }
    }

    // --- 3.: subscription burst is a hard cap ---
    #[derive(sqlx::FromRow)]
    struct SubRow {
        pk_alloc: String,
        str_name: String,
        int_burst: i64,
    }
    let subs: Vec<SubRow> = sqlx::query_as(
        "SELECT s.pk_alloc, a.str_name, s.int_burst \
         FROM subscription s JOIN alloc a ON a.pk_alloc = s.pk_alloc WHERE s.pk_show = $1",
    )
    .bind(&show)
    .fetch_all(pool)
    .await
    .expect("subscription query");
    for sub in &subs {
        let alloc = Uuid::parse_str(&sub.pk_alloc).expect("alloc uuid");
        let booked_centi = exp_sub.get(&(show_id, alloc)).map(|(c, _)| *c).unwrap_or(0);
        let booked_cores = booked_centi / CORE_MULT;
        let burst_cores = sub.int_burst / CORE_MULT;
        if booked_cores > burst_cores {
            out.violations.push(format!(
                "subscription {}: booked {booked_cores} cores exceeds burst {burst_cores}",
                sub.str_name
            ));
        }
        out.per_sub.push(SubUsage {
            alloc_name: sub.str_name.clone(),
            booked_cores,
            burst_cores,
        });
    }

    // --- 4.: job max-cores is a hard cap ---
    let job_cap_breaches: i64 = sqlx::query_scalar(
        "SELECT count(*) FROM ( \
             SELECT p.pk_job FROM proc p \
             JOIN job_resource jr ON jr.pk_job = p.pk_job \
             JOIN job j ON j.pk_job = p.pk_job \
             WHERE j.pk_show = $1 AND jr.int_max_cores > 0 \
             GROUP BY p.pk_job, jr.int_max_cores \
             HAVING SUM(p.int_cores_reserved) > jr.int_max_cores) x",
    )
    .bind(&show)
    .fetch_one(pool)
    .await
    .expect("job cap query");
    if job_cap_breaches > 0 {
        out.violations.push(format!(
            "{job_cap_breaches} jobs booked above job_resource.int_max_cores"
        ));
    }

    // --- 5.: host core ledger ---
    let host_mismatches: i64 = sqlx::query_scalar(
        "SELECT count(*) FROM host h \
         LEFT JOIN (SELECT pk_host, SUM(int_cores_reserved) AS cores FROM proc GROUP BY pk_host) p \
                ON p.pk_host = h.pk_host \
         WHERE h.str_name LIKE $1 \
           AND (h.int_cores_idle < 0 OR h.int_cores - h.int_cores_idle <> COALESCE(p.cores, 0))",
    )
    .bind(&like)
    .fetch_one(pool)
    .await
    .expect("host ledger query");
    if host_mismatches > 0 {
        out.violations.push(format!(
            "{host_mismatches} hosts where int_cores - int_cores_idle != SUM(proc) or idle < 0"
        ));
    }

    // --- 6.: frame/proc agreement ---
    let (running_frames, procs): (i64, i64) = sqlx::query_as(
        "SELECT \
           (SELECT count(*) FROM frame f JOIN job j ON j.pk_job = f.pk_job \
             WHERE j.pk_show = $1 AND f.str_state = 'RUNNING'), \
           (SELECT count(*) FROM proc WHERE pk_show = $1)",
    )
    .bind(&show)
    .fetch_one(pool)
    .await
    .expect("frame/proc query");
    if running_frames != procs {
        out.violations
            .push(format!("{running_frames} RUNNING frames but {procs} procs"));
    }

    // --- 7.: trigger-maintained stats agree with the frame table ---
    let (stat_waiting, frame_waiting): (i64, i64) = sqlx::query_as(
        "SELECT \
           (SELECT COALESCE(SUM(js.int_waiting_count), 0)::bigint FROM job_stat js \
             JOIN job j ON j.pk_job = js.pk_job WHERE j.pk_show = $1), \
           (SELECT count(*) FROM frame f JOIN job j ON j.pk_job = f.pk_job \
             WHERE j.pk_show = $1 AND f.str_state = 'WAITING')",
    )
    .bind(&show)
    .fetch_one(pool)
    .await
    .expect("waiting stat query");
    if stat_waiting != frame_waiting {
        out.violations.push(format!(
            "job_stat says {stat_waiting} waiting frames but frame table says {frame_waiting}"
        ));
    }

    out.dispatched_procs = procs;
    out.booked_cores = exp_sub.values().map(|(c, _)| c / CORE_MULT).sum();
    out
}

// =============================================================================
// Throughput stats
// =============================================================================

#[derive(Debug)]
pub struct BookingStats {
    pub dispatched: i64,
    pub first_booked: Option<DateTime<Utc>>,
    pub last_booked: Option<DateTime<Utc>>,
}

impl BookingStats {
    /// Frames booked per second over the active booking window (first to last
    /// proc insert), which excludes the post-drain shutdown tail of the feed.
    pub fn frames_per_sec(&self) -> f64 {
        match (self.first_booked, self.last_booked) {
            (Some(first), Some(last)) if self.dispatched > 1 => {
                let secs = (last - first).num_milliseconds() as f64 / 1000.0;
                if secs > 0.0 {
                    (self.dispatched - 1) as f64 / secs
                } else {
                    f64::INFINITY
                }
            }
            _ => 0.0,
        }
    }
}

pub async fn booking_stats(pool: &Pool<Postgres>, show_id: Uuid) -> BookingStats {
    let (dispatched, first_booked, last_booked): (
        i64,
        Option<DateTime<Utc>>,
        Option<DateTime<Utc>>,
    ) = sqlx::query_as(
        "SELECT count(*), min(ts_booked), max(ts_booked) FROM proc WHERE pk_show = $1",
    )
    .bind(show_id.to_string())
    .fetch_one(pool)
    .await
    .expect("booking stats query");
    BookingStats {
        dispatched,
        first_booked,
        last_booked,
    }
}

// =============================================================================
// Cleanup
// =============================================================================

/// Builds a `LIKE` pattern matching exactly `prefix` followed by anything.
/// The prefix's own `_` and `%` are LIKE metacharacters, so they are escaped
/// (backslash is Postgres's default LIKE escape) - otherwise a prefix like
/// `stress_` would also match `stressX...` and risk deleting unrelated rows.
fn like_prefix(prefix: &str) -> String {
    let escaped = prefix
        .replace('\\', "\\\\")
        .replace('_', "\\_")
        .replace('%', "\\%");
    format!("{escaped}%")
}

/// Deletes every row created by stress runs whose name starts with `prefix`,
/// including rows created behind our back by schema triggers (history/stat
/// tables) and by dispatching (proc, RUNNING frames). Runs with triggers
/// disabled so the sweep is order-insensitive and doesn't fire history triggers.
pub async fn clean_up_stress_data(pool: &Pool<Postgres>, prefix: &str) -> Result<(), sqlx::Error> {
    let like = like_prefix(prefix);
    let mut tx = pool.begin().await?;
    sqlx::query("SET session_replication_role = 'replica'")
        .execute(&mut *tx)
        .await?;

    const JOB_SUBQUERY: &str = "(SELECT pk_job FROM job WHERE str_name LIKE $1)";
    let by_job_tables = [
        "proc",
        "frame_history",
        "frame",
        "layer_stat",
        "layer_resource",
        "layer_mem",
        "layer_usage",
        "layer_history",
        "job_stat",
        "job_resource",
        "job_mem",
        "job_usage",
        "job_history",
        "comments",
    ];
    for table in by_job_tables {
        sqlx::query(&format!(
            "DELETE FROM {table} WHERE pk_job IN {JOB_SUBQUERY}"
        ))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    }
    for table in ["layer_env", "layer_output"] {
        sqlx::query(&format!(
            "DELETE FROM {table} WHERE pk_layer IN \
             (SELECT pk_layer FROM layer WHERE pk_job IN {JOB_SUBQUERY})"
        ))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    }
    sqlx::query(&format!("DELETE FROM layer WHERE pk_job IN {JOB_SUBQUERY}"))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    sqlx::query("DELETE FROM job WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;

    for table in ["host_tag", "host_stat", "host_local"] {
        sqlx::query(&format!(
            "DELETE FROM {table} WHERE pk_host IN (SELECT pk_host FROM host WHERE str_name LIKE $1)"
        ))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    }
    sqlx::query("DELETE FROM host WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;

    const SHOW_SUBQUERY: &str = "(SELECT pk_show FROM show WHERE str_name LIKE $1)";
    for table in ["point", "show_service", "show_alias"] {
        sqlx::query(&format!(
            "DELETE FROM {table} WHERE pk_show IN {SHOW_SUBQUERY}"
        ))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    }
    for table in ["folder_resource", "folder_level"] {
        sqlx::query(&format!(
            "DELETE FROM {table} WHERE pk_folder IN \
             (SELECT pk_folder FROM folder WHERE pk_show IN {SHOW_SUBQUERY})"
        ))
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    }
    sqlx::query(&format!(
        "DELETE FROM folder WHERE pk_show IN {SHOW_SUBQUERY}"
    ))
    .bind(&like)
    .execute(&mut *tx)
    .await?;
    sqlx::query(
        "DELETE FROM subscription WHERE pk_alloc IN (SELECT pk_alloc FROM alloc WHERE str_name LIKE $1)",
    )
    .bind(&like)
    .execute(&mut *tx)
    .await?;
    sqlx::query("DELETE FROM show WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    sqlx::query("DELETE FROM alloc WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    sqlx::query("DELETE FROM dept WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;
    sqlx::query("DELETE FROM facility WHERE str_name LIKE $1")
        .bind(&like)
        .execute(&mut *tx)
        .await?;

    sqlx::query("SET session_replication_role = 'origin'")
        .execute(&mut *tx)
        .await?;
    tx.commit().await
}

/// Counts rows still matching the prefix in every named table the suite touches.
/// Used after cleanup to prove nothing leaked into the shared test database.
pub async fn residue_counts(pool: &Pool<Postgres>, prefix: &str) -> Vec<(&'static str, i64)> {
    let like = like_prefix(prefix);
    let mut residue = Vec::new();
    let named = [
        ("job", "SELECT count(*) FROM job WHERE str_name LIKE $1"),
        ("layer", "SELECT count(*) FROM layer WHERE str_name LIKE $1"),
        ("frame", "SELECT count(*) FROM frame WHERE str_name LIKE $1"),
        ("host", "SELECT count(*) FROM host WHERE str_name LIKE $1"),
        (
            "host_tag",
            "SELECT count(*) FROM host_tag WHERE str_tag LIKE $1",
        ),
        ("alloc", "SELECT count(*) FROM alloc WHERE str_name LIKE $1"),
        ("show", "SELECT count(*) FROM show WHERE str_name LIKE $1"),
        (
            "folder",
            "SELECT count(*) FROM folder WHERE str_name LIKE $1",
        ),
        ("dept", "SELECT count(*) FROM dept WHERE str_name LIKE $1"),
        (
            "facility",
            "SELECT count(*) FROM facility WHERE str_name LIKE $1",
        ),
    ];
    for (table, sql) in named {
        let count: i64 = sqlx::query_scalar(sql)
            .bind(&like)
            .fetch_one(pool)
            .await
            .unwrap_or(0);
        if count > 0 {
            residue.push((table, count));
        }
    }
    residue
}
