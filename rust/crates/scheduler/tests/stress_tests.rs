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

mod util;

#[cfg(all(test, feature = "smoke-tests"))]

mod stress_test {
    use crate::util::WaitingFrameClause;
    use std::{sync::atomic::Ordering, time::SystemTime};

    use scheduler::{
        cluster::{self, ClusterFeed},
        config::OVERRIDE_CONFIG,
        host_cache, pipeline,
    };
    use tokio_test::assert_ok;
    use tracing::info;
    use tracing_test::traced_test;
    use uuid::Uuid;

    use super::*;
    use crate::util::{
        clean_up_test_data, create_test_config, create_test_data, get_waiting_frames_count,
        TestData,
    };

    struct TestDescription {
        test_name: String,
        job_count: usize,
        host_count: usize,
        layer_count: usize,
        frames_per_layer_count: usize,
        tag_count: usize,
    }

    impl TestDescription {
        pub fn total_frames(&self) -> usize {
            self.job_count * self.layer_count * self.frames_per_layer_count
        }
    }

    async fn setup(test_description: &TestDescription) -> Result<TestData, sqlx::Error> {
        let test_id = Uuid::new_v4().to_string()[..8].to_string();

        create_test_data(
            &test_description.test_name,
            &test_id,
            test_description.job_count,
            test_description.host_count,
            test_description.layer_count,
            test_description.frames_per_layer_count,
            test_description.tag_count,
        )
        .await
    }

    async fn tear_down(test_prefix: &str) -> Result<(), sqlx::Error> {
        clean_up_test_data(test_prefix).await
    }

    #[actix::test]
    // #[traced_test]
    async fn test_stress_small() {
        let desc = TestDescription {
            test_name: "sts".to_string(),
            job_count: 200,
            host_count: 1000,
            layer_count: 4,
            frames_per_layer_count: 2,
            tag_count: 4,
        };
        let _ = tracing_subscriber::fmt()
            .with_max_level(tracing::Level::INFO)
            .with_ansi(true)
            .try_init();

        // Set global config
        let _ = OVERRIDE_CONFIG.set(create_test_config());
        let test_data = assert_ok!(setup(&desc).await);

        let cluster_len = test_data.clusters.len();
        let cluster_feed = ClusterFeed::load_from_clusters(test_data.clusters, &[]);
        info!(
            "Starting Small stress test {} - cluster size: {:?}",
            test_data.test_prefix, cluster_len
        );

        let waiting_frames_before =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(test_data.test_prefix.clone()))
                .await;
        assert_eq!(waiting_frames_before, desc.total_frames());

        let start_time = SystemTime::now();
        // Run job dispatcher
        assert_ok!(pipeline::run(cluster_feed).await);

        let duration = start_time.elapsed().unwrap().as_secs();
        info!("Processed Frames: {} at {}s", desc.total_frames(), duration);
        info!(
            "Host attempts: {}",
            pipeline::HOSTS_ATTEMPTED.load(Ordering::Relaxed)
        );
        info!(
            "Wasted attempts: {}%",
            (pipeline::WASTED_ATTEMPTS.load(Ordering::Relaxed) as f32
                / pipeline::HOSTS_ATTEMPTED.load(Ordering::Relaxed) as f32)
                * 100.0
        );
        info!(
            "Cluster rounds: {}",
            cluster::CLUSTER_ROUNDS.load(Ordering::Relaxed)
        );
        info!("HostCache hit ratio = {}%", host_cache::hit_ratio().await);

        let waiting_frames_after =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(test_data.test_prefix.clone()))
                .await;

        // Clean up test data
        assert_ok!(tear_down(&test_data.test_prefix).await);

        // Ensure reminder is less than 10%
        assert!(waiting_frames_after < (desc.total_frames() as f64 * 0.1) as usize);
    }
}
