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

//! Awake-gate superset guard, kept in its own test binary.
//!
//! This lives apart from `stress_tests.rs` on purpose: `OVERRIDE_CONFIG` is a
//! process-global `OnceCell` (first-writer-wins), and this test installs its own
//! static config. Sharing a process with `stress_booking_and_accounting` would
//! let whichever runs first pin the config, so this test's config could clobber
//! the booking suite's dynamic testcontainer port (or vice-versa). A separate
//! binary = a separate process = a private `OVERRIDE_CONFIG`, so neither can race
//! the other.

mod util;

#[cfg(all(test, feature = "stress-tests"))]
mod active_scan_suite {
    use std::collections::HashSet;

    use scheduler::config::OVERRIDE_CONFIG;
    use scheduler::dao::JobDao;
    use tokio_test::assert_ok;
    use uuid::Uuid;

    use crate::util::stress::{clean_up_stress_data, create_stress_config, seed_farm, FarmSpec};
    use crate::util::test_connection_pool;

    /// Guards the awake-gate scan's superset invariant against the live SQL:
    /// for every cluster the per-cluster dispatch query returns a job for, the
    /// scan must surface at least one of that cluster's tags. A regression that
    /// over-narrows `QUERY_ACTIVE_TAGS` (dropping a needed row) would starve
    /// that cluster's jobs; this catches it directly against Postgres. It only
    /// needs a migrated database.
    #[actix::test]
    async fn stress_active_scan_is_superset_of_per_cluster_query() {
        // This test never books, so accounting is inert here. This binary's
        // OVERRIDE_CONFIG is private to its own process (see module docs).
        let _ = OVERRIDE_CONFIG.set(create_stress_config());

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
