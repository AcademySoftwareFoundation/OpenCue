mod util;

use crate::util::WaitingFrameClause;

mod stress_test {
    use std::{sync::atomic::Ordering, time::SystemTime};

    use scheduler::{cluster::ClusterFeed, config::OVERRIDE_CONFIG, host_cache, pipeline};
    use tokio_test::assert_ok;
    use tracing::info;
    use tracing_test::traced_test;
    use uuid::Uuid;

    use super::*;
    use crate::util::{
        TestData, clean_up_test_data, create_test_config, create_test_data,
        get_waiting_frames_count,
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

    // #[tokio::test(flavor = "multi_thread", worker_threads = 8)]
    #[actix::test]
    #[traced_test]
    async fn test_stress_small() {
        let desc = TestDescription {
            test_name: "sts".to_string(),
            job_count: 2000,
            host_count: 8000,
            layer_count: 4,
            frames_per_layer_count: 2,
            tag_count: 4,
        };
        let _ = tracing_subscriber::fmt()
            .with_max_level(tracing::Level::INFO)
            .try_init();

        // Set global config
        let _ = OVERRIDE_CONFIG.set(create_test_config());
        let test_data = assert_ok!(setup(&desc).await);

        let cluster_len = test_data.clusters.len();
        let cluster_feed = ClusterFeed::new_for_test(test_data.clusters);
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
            pipeline::HOST_CYCLES.load(Ordering::Relaxed)
        );
        info!("HostCache hit ratio = {}%", host_cache::hit_ratio().await);

        let waiting_frames_after =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(test_data.test_prefix.clone()))
                .await;

        // Clean up test data
        // TODO: call hangs forever
        assert_ok!(tear_down(&test_data.test_prefix).await);

        assert_eq!(waiting_frames_after, 0);
    }
}
