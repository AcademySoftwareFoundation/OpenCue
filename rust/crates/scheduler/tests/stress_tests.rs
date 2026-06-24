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

//! Booking + accounting stress suite for the Rust scheduler.
//!
//! Runs the full production pipeline (`pipeline::run`: Redis accounting bootstrap →
//! cluster feed → job query → host matching → dispatch) against a realistic farm in
//! two phases inside one process:
//!
//! 1. **drain** — farm capacity comfortably exceeds demand. Benchmarks booking
//!    throughput (frames/s over the active booking window) and requires ≥90%
//!    (`STRESS_DRAIN_TARGET`) of frames to dispatch.
//! 2. **saturation** — demand vastly exceeds tight subscription bursts and per-job
//!    core caps, so the Redis Lua cap check becomes the binding constraint. Verifies
//!    enforcement (no booking above burst / job max-cores) and that rejections
//!    actually flowed through the accounting hot path.
//!
//! After each phase, an audit cross-checks every Redis `acct:*` hash against
//! `SUM(proc)` in Postgres plus host/frame/stat invariants — with the recompute and
//! limit-reseed loops pushed beyond the test horizon, agreement proves the dispatch
//! hot path (Lua book + force-rollback) kept accounting exact on its own.
//!
//! # Requirements
//!
//! - Postgres with migrations applied, from the repo root: `docker compose up -d flyway`
//! - A Docker daemon (the suite starts a throwaway Redis container via testcontainers;
//!   all Redis state dies with the container)
//!
//! # Running
//!
//! ```bash
//! cargo test -p scheduler --features stress-tests --test stress_tests -- --nocapture
//! ```
//!
//! All `stress_%`-prefixed rows are swept from Postgres before seeding and after the
//! run, and the suite asserts none remain.
//!
//! # Tuning (env vars)
//!
//! | var                       | default | meaning                                  |
//! |---------------------------|---------|------------------------------------------|
//! | `STRESS_JOBS`             | 300     | drain-phase job count                     |
//! | `STRESS_LAYERS`           | 4       | drain-phase layers per job                |
//! | `STRESS_FRAMES_PER_LAYER` | 5       | drain-phase frames per layer              |
//! | `STRESS_HOSTS`            | 1200    | drain-phase host count                    |
//! | `STRESS_TAGS`             | 8       | drain-phase manual tag count              |
//! | `STRESS_SAT_JOBS`         | 150     | saturation-phase job count                |
//! | `STRESS_SAT_HOSTS`        | 400     | saturation-phase host count               |
//! | `STRESS_DRAIN_TARGET`     | 0.9     | fraction of drain frames that must book   |
//! | `STRESS_STALL_SECS`       | 30      | watchdog: pause jobs after no progress    |
//! | `STRESS_TIMEOUT_SECS`     | 600     | watchdog: per-phase hard timeout          |
//!
//! # CI
//!
//! Runs in `.github/workflows/scheduler-stress-pipeline.yml`: on PRs touching the
//! scheduler crate or DB migrations, nightly on master, and on demand with custom
//! scale. Correctness assertions gate the job; throughput is informational only.
//! Full guide: `docs/_docs/developer-guide/scheduler-stress-testing.md`.

mod util;

#[cfg(all(test, feature = "stress-tests"))]
mod stress_suite {
    use std::sync::atomic::Ordering;
    use std::time::{Duration, Instant};

    use redis::aio::ConnectionManager;
    use redis::AsyncCommands;
    use scheduler::{
        cluster::{self, ClusterFeed},
        config::OVERRIDE_CONFIG,
        host_cache, metrics, pipeline,
    };
    use testcontainers::runners::AsyncRunner;
    use testcontainers_modules::redis::Redis as RedisImage;
    use tokio_test::assert_ok;
    use tracing::info;
    use uuid::Uuid;

    use crate::util::stress::{
        audit_accounting, booking_stats, clean_up_stress_data, create_stress_config,
        residue_counts, seed_farm, spawn_stall_watchdog, AuditOutcome, BookingStats, FarmSpec,
        StressFarm, WatchdogOutcome,
    };
    use crate::util::{get_waiting_frames_count, test_connection_pool, WaitingFrameClause};

    /// Every table label the booking Lua can reject on.
    const LIMIT_TABLES: [&str; 5] = ["subscription", "folder", "job", "folder_gpus", "job_gpus"];

    fn env_usize(name: &str, default: usize) -> usize {
        std::env::var(name)
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(default)
    }

    fn env_f64(name: &str, default: f64) -> f64 {
        std::env::var(name)
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(default)
    }

    /// Snapshot of the process-wide counters surrounding a phase, so each phase
    /// reports deltas rather than session totals.
    #[derive(Debug, Clone)]
    struct Counters {
        hosts_attempted: usize,
        wasted_attempts: usize,
        cluster_rounds: usize,
        frames_dispatched: u64,
        limit_exceeded: Vec<(&'static str, u64)>,
        redis_seq: i64,
    }

    impl Counters {
        async fn take(redis: &mut ConnectionManager) -> Counters {
            let seq: Option<i64> = redis.get("acct:seq").await.unwrap_or(None);
            Counters {
                hosts_attempted: pipeline::HOSTS_ATTEMPTED.load(Ordering::Relaxed),
                wasted_attempts: pipeline::WASTED_ATTEMPTS.load(Ordering::Relaxed),
                cluster_rounds: cluster::CLUSTER_ROUNDS.load(Ordering::Relaxed),
                frames_dispatched: metrics::frames_dispatched_session(),
                limit_exceeded: LIMIT_TABLES
                    .iter()
                    .map(|table| {
                        let count = metrics::ACCOUNTING_LIMIT_EXCEEDED_TOTAL
                            .with_label_values(&[table])
                            .get() as u64;
                        (*table, count)
                    })
                    .collect(),
                redis_seq: seq.unwrap_or(0),
            }
        }

        fn limit_exceeded_delta(&self, before: &Counters, table: &str) -> u64 {
            let after = self
                .limit_exceeded
                .iter()
                .find(|(t, _)| *t == table)
                .map(|(_, c)| *c)
                .unwrap_or(0);
            let before = before
                .limit_exceeded
                .iter()
                .find(|(t, _)| *t == table)
                .map(|(_, c)| *c)
                .unwrap_or(0);
            after.saturating_sub(before)
        }
    }

    struct PhaseResult {
        name: &'static str,
        total_frames: usize,
        waiting_before: usize,
        waiting_after: usize,
        stats: BookingStats,
        wall: Duration,
        before: Counters,
        after: Counters,
        cache_hit_pct: usize,
        watchdog: Option<WatchdogOutcome>,
        timed_out: bool,
        audit: AuditOutcome,
    }

    impl PhaseResult {
        fn print(&self) {
            let drained_pct =
                100.0 * self.stats.dispatched as f64 / self.total_frames.max(1) as f64;
            println!("\n================ phase: {} ================", self.name);
            println!(
                "frames     : {} seeded, {} dispatched ({:.1}%), waiting {} -> {}",
                self.total_frames,
                self.stats.dispatched,
                drained_pct,
                self.waiting_before,
                self.waiting_after
            );
            let window = match (self.stats.first_booked, self.stats.last_booked) {
                (Some(first), Some(last)) => (last - first).num_milliseconds() as f64 / 1000.0,
                _ => 0.0,
            };
            println!(
                "throughput : {:.1} frames/s over a {:.1}s booking window (wall {:.1}s)",
                self.stats.frames_per_sec(),
                window,
                self.wall.as_secs_f64()
            );
            println!(
                "matching   : {} host attempts ({:.1}% wasted), {} cluster rounds, host-cache hit {}%",
                self.after.hosts_attempted - self.before.hosts_attempted,
                100.0 * (self.after.wasted_attempts - self.before.wasted_attempts) as f64
                    / (self.after.hosts_attempted - self.before.hosts_attempted).max(1) as f64,
                self.after.cluster_rounds - self.before.cluster_rounds,
                self.cache_hit_pct
            );
            let rejections: Vec<String> = LIMIT_TABLES
                .iter()
                .map(|t| format!("{}={}", t, self.after.limit_exceeded_delta(&self.before, t)))
                .collect();
            println!(
                "accounting : {} redis lua ops, {} dispatches (metrics), {} booked cores, rejections [{}]",
                self.after.redis_seq - self.before.redis_seq,
                self.after.frames_dispatched - self.before.frames_dispatched,
                self.audit.booked_cores,
                rejections.join(" ")
            );
            for sub in &self.audit.per_sub {
                println!(
                    "             {}: {}/{} cores",
                    sub.alloc_name, sub.booked_cores, sub.burst_cores
                );
            }
            println!(
                "watchdog   : {:?}{}",
                self.watchdog,
                if self.timed_out {
                    " (HARD TIMEOUT)"
                } else {
                    ""
                }
            );
            if self.audit.violations.is_empty() {
                println!("audit      : OK");
            } else {
                println!("audit      : {} VIOLATIONS", self.audit.violations.len());
                for violation in &self.audit.violations {
                    println!("  - {}", violation);
                }
            }
        }
    }

    async fn run_phase(
        name: &'static str,
        farm: &StressFarm,
        redis: &mut ConnectionManager,
        stall: Duration,
        hard_timeout: Duration,
    ) -> PhaseResult {
        let pool = assert_ok!(test_connection_pool().await);
        let waiting_before =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(farm.prefix.clone())).await;
        let before = Counters::take(redis).await;

        info!(
            "Starting phase '{}' ({} clusters, {} frames)",
            name,
            farm.clusters.len(),
            farm.spec.total_frames()
        );
        let watchdog = spawn_stall_watchdog(pool.clone(), farm.prefix.clone(), stall, hard_timeout);

        let feed = ClusterFeed::load_from_clusters(farm.clusters.clone(), &[]);
        let started = Instant::now();
        // The fuse only trips if the watchdog's job-pausing failed to stop the feed;
        // dropping the run mid-flight is a last resort that the audit will flag.
        let run =
            tokio::time::timeout(hard_timeout + Duration::from_secs(60), pipeline::run(feed)).await;
        let wall = started.elapsed();
        let timed_out = match run {
            Ok(result) => {
                assert_ok!(result, "pipeline::run failed in phase {}", name);
                false
            }
            Err(_) => true,
        };

        let watchdog_outcome = if watchdog.is_finished() {
            watchdog.await.ok()
        } else {
            watchdog.abort();
            None
        };

        let after = Counters::take(redis).await;
        let cache_hit_pct = host_cache::hit_ratio().await;
        let stats = booking_stats(&pool, farm.show_id).await;
        let waiting_after =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(farm.prefix.clone())).await;
        let audit = audit_accounting(&pool, redis, farm).await;

        PhaseResult {
            name,
            total_frames: farm.spec.total_frames(),
            waiting_before,
            waiting_after,
            stats,
            wall,
            before,
            after,
            cache_hit_pct,
            watchdog: watchdog_outcome,
            timed_out,
            audit,
        }
    }

    #[actix::test]
    async fn stress_booking_and_accounting() {
        let _ = tracing_subscriber::fmt()
            .with_max_level(tracing::Level::INFO)
            .with_ansi(true)
            .try_init();

        let stall = Duration::from_secs(env_usize("STRESS_STALL_SECS", 30) as u64);
        let hard_timeout = Duration::from_secs(env_usize("STRESS_TIMEOUT_SECS", 600) as u64);
        let drain_target = env_f64("STRESS_DRAIN_TARGET", 0.9);

        // Throwaway Redis for the accounting hot path; all acct:* state dies with it.
        let redis_container = RedisImage::default()
            .start()
            .await
            .expect("failed to start Redis testcontainer (is Docker running?)");
        let redis_port = redis_container
            .get_host_port_ipv4(6379)
            .await
            .expect("redis port");
        let _ = OVERRIDE_CONFIG.set(create_stress_config(redis_port));
        let redis_client =
            redis::Client::open(format!("redis://127.0.0.1:{redis_port}/")).expect("redis client");
        let mut redis = ConnectionManager::new(redis_client)
            .await
            .expect("redis connection");

        let pool = assert_ok!(test_connection_pool().await);

        // Sweep leftovers from previous (possibly aborted) runs before seeding.
        assert_ok!(clean_up_stress_data(&pool, "stress_").await);

        // 6-char id keeps every generated name inside the tightest schema limits
        // (alloc.str_tag VARCHAR(24), host.str_name VARCHAR(30)).
        let run_id = Uuid::new_v4().to_string()[..6].to_string();

        // Phase 1: capacity >> demand. Every frame should find a host; subscription
        // bursts and job caps are effectively unlimited so raw booking throughput
        // and exact hot-path accounting are what's measured.
        let drain_spec = FarmSpec {
            prefix: format!("stress_d_{run_id}"),
            alloc_count: 3,
            host_count: env_usize("STRESS_HOSTS", 1200),
            host_cores_choices: (16..=128).step_by(8).collect(),
            host_mem_gb_range: (32, 256),
            sub_size_cores: 90_000,
            sub_burst_cores: 90_000,
            manual_tag_count: env_usize("STRESS_TAGS", 8),
            job_count: env_usize("STRESS_JOBS", 300),
            layers_per_job: env_usize("STRESS_LAYERS", 4),
            frames_per_layer: env_usize("STRESS_FRAMES_PER_LAYER", 5),
            layer_cores_choices: vec![1, 2, 4, 8],
            layer_mem_gb_range: (2, 8),
            // Effectively unlimited but > 0 (0 hides the show from vs_waiting).
            job_max_cores: 100_000,
        };

        // Phase 2: demand >> caps. Three tight subscription bursts plus a per-job
        // max-cores cap make the Redis Lua the binding constraint; most dispatch
        // attempts must be rejected by it without ever breaching a cap.
        let sat_spec = FarmSpec {
            prefix: format!("stress_s_{run_id}"),
            alloc_count: 3,
            host_count: env_usize("STRESS_SAT_HOSTS", 400),
            host_cores_choices: vec![8, 16, 32],
            host_mem_gb_range: (32, 64),
            sub_size_cores: 150,
            sub_burst_cores: 150,
            manual_tag_count: 4,
            job_count: env_usize("STRESS_SAT_JOBS", 150),
            layers_per_job: 2,
            frames_per_layer: 10,
            layer_cores_choices: vec![2, 4],
            layer_mem_gb_range: (2, 4),
            job_max_cores: 20,
        };

        // Seed both farms up front so the accounting service's managed-shows cache
        // (populated on first pipeline::run) covers both shows from the start.
        let seed_started = Instant::now();
        let drain_farm = assert_ok!(seed_farm(&pool, drain_spec).await);
        let sat_farm = assert_ok!(seed_farm(&pool, sat_spec).await);
        info!("Seeding took {:?}", seed_started.elapsed());

        let drain = run_phase("drain", &drain_farm, &mut redis, stall, hard_timeout).await;
        let sat = run_phase("saturation", &sat_farm, &mut redis, stall, hard_timeout).await;

        drain.print();
        sat.print();

        // Collect all failures before tearing down, so the database is left clean
        // even when assertions fail.
        let mut failures: Vec<String> = Vec::new();

        if drain.timed_out {
            failures.push("drain phase hit the hard timeout fuse".to_string());
        }
        for violation in &drain.audit.violations {
            failures.push(format!("drain audit: {violation}"));
        }
        let drained = drain.stats.dispatched as f64 / drain.total_frames.max(1) as f64;
        if drained < drain_target {
            failures.push(format!(
                "drain phase dispatched only {:.1}% of frames (target {:.0}%)",
                drained * 100.0,
                drain_target * 100.0
            ));
        }

        if sat.timed_out {
            failures.push("saturation phase hit the hard timeout fuse".to_string());
        }
        if sat.watchdog == Some(WatchdogOutcome::TimedOut) {
            failures.push("saturation phase never converged (watchdog hard timeout)".to_string());
        }
        for violation in &sat.audit.violations {
            failures.push(format!("saturation audit: {violation}"));
        }
        let total_burst: i64 = sat.audit.per_sub.iter().map(|s| s.burst_cores).sum();
        if sat.audit.booked_cores * 2 < total_burst {
            failures.push(format!(
                "saturation booked only {} of {} burst cores (expected >= 50%)",
                sat.audit.booked_cores, total_burst
            ));
        }
        if sat.after.limit_exceeded_delta(&sat.before, "subscription") == 0 {
            failures.push(
                "saturation phase produced no subscription-cap rejections in the Redis hot path"
                    .to_string(),
            );
        }

        // Tear down everything this suite ever created and prove it's gone.
        assert_ok!(clean_up_stress_data(&pool, "stress_").await);
        let residue = residue_counts(&pool, "stress_").await;
        if !residue.is_empty() {
            failures.push(format!("rows left behind after cleanup: {residue:?}"));
        }

        assert!(
            failures.is_empty(),
            "stress suite failed:\n  - {}",
            failures.join("\n  - ")
        );
    }

    /// Guards the awake-gate scan's superset invariant against the live SQL:
    /// for every cluster the per-cluster dispatch query returns a job for, the
    /// scan must surface at least one of that cluster's tags. A regression that
    /// over-narrows `QUERY_ACTIVE_TAGS` (dropping a needed row) would starve
    /// that cluster's jobs; this catches it directly against Postgres. Pure-PG
    /// (no Redis), so it only needs a migrated database.
    #[actix::test]
    async fn stress_active_scan_is_superset_of_per_cluster_query() {
        use scheduler::dao::JobDao;
        use std::collections::HashSet;

        // create_stress_config needs a Redis port for its accounting section, but
        // this test never books, so the port is never dialed. OnceCell set is a
        // no-op if the stress suite already configured CONFIG.
        let _ = OVERRIDE_CONFIG.set(create_stress_config(6379));

        let pool = assert_ok!(test_connection_pool().await);
        let prefix = format!("stress_sc_{}", &Uuid::new_v4().to_string()[..6]);
        assert_ok!(clean_up_stress_data(&pool, &prefix).await);

        // Small mixed farm: a couple of allocs and manual tags, several jobs with
        // waiting frames and generous caps so the per-cluster query returns work.
        let spec = FarmSpec {
            prefix: prefix.clone(),
            alloc_count: 2,
            host_count: 6,
            host_cores_choices: vec![16, 32],
            host_mem_gb_range: (32, 64),
            sub_size_cores: 90_000,
            sub_burst_cores: 90_000,
            manual_tag_count: 3,
            job_count: 5,
            layers_per_job: 2,
            frames_per_layer: 2,
            layer_cores_choices: vec![1, 2],
            layer_mem_gb_range: (2, 4),
            job_max_cores: 100_000,
        };
        let farm = assert_ok!(seed_farm(&pool, spec).await);

        let job_dao = assert_ok!(JobDao::new()
            .await
            .map_err(|e| sqlx::Error::Configuration(e.to_string().into())));
        let facility = farm.facility_id.to_string();
        let active = job_dao
            .scan_active_tags(Some(&facility))
            .await
            .expect("scan_active_tags");
        let active_set: HashSet<(String, String, String)> = active
            .iter()
            .map(|r| (r.pk_facility.clone(), r.pk_show.clone(), r.tag.clone()))
            .collect();

        // No false negatives: any cluster with a dispatchable job must be covered.
        let mut checked_with_jobs = 0usize;
        for cluster in &farm.clusters {
            let jobs = job_dao
                .query_pending_jobs_by_show_facility_and_tags(
                    cluster.show_id,
                    &cluster.facility_id,
                    cluster.tags.iter().map(|t| t.name.clone()),
                )
                .await
                .expect("per-cluster query");
            if jobs.is_empty() {
                continue;
            }
            checked_with_jobs += 1;
            let covered = cluster.tags.iter().any(|t| {
                active_set.contains(&(
                    cluster.facility_id.clone(),
                    cluster.show_id.to_string(),
                    t.name.clone(),
                ))
            });
            assert!(
                covered,
                "awake scan missed cluster {cluster} which has {} dispatchable job(s)",
                jobs.len()
            );
        }
        assert!(
            checked_with_jobs > 0,
            "test seeded no dispatchable clusters; superset check was vacuous"
        );

        assert_ok!(clean_up_stress_data(&pool, &prefix).await);
    }
}
