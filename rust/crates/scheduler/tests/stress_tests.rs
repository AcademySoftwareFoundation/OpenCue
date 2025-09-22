mod util;

use crate::util::WaitingFrameClause;

mod stress_test {
    use scheduler::{cluster::ClusterFeed, config::OVERRIDE_CONFIG, job_fetcher};
    use serial_test::serial;
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

    async fn setup(test_description: TestDescription) -> Result<TestData, sqlx::Error> {
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

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_stress_small() {
        let desc = TestDescription {
            test_name: "sts".to_string(),
            job_count: 10,
            host_count: 40,
            layer_count: 2,
            frames_per_layer_count: 2,
            tag_count: 4,
        };

        // Set global config
        let _ = OVERRIDE_CONFIG.set(create_test_config());
        let test_data = assert_ok!(setup(desc).await);

        let cluster_feed = ClusterFeed::new_for_test(test_data.clusters);
        info!(
            "Starting Small stress test {} - cluster: {:?}",
            test_data.test_prefix, cluster_feed
        );

        let waiting_frames_before =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(test_data.test_prefix.clone()))
                .await;
        assert_eq!(waiting_frames_before, 40);

        assert_ok!(job_fetcher::run(cluster_feed).await);

        let waiting_frames_after =
            get_waiting_frames_count(WaitingFrameClause::JobPrefix(test_data.test_prefix.clone()))
                .await;

        // Clean up test data
        // TODO: call hangs forever
        assert_ok!(tear_down(&test_data.test_prefix).await);

        assert_eq!(waiting_frames_after, 0);
    }
}
