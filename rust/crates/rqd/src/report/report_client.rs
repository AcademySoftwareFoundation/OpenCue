use std::time::{Duration, SystemTime};

use crate::config::{Config, GrpcConfig};
use async_trait::async_trait;
use chrono::{DateTime, Local};
use miette::{IntoDiagnostic, Result, miette};
use opencue_proto::report::{self as pb, rqd_report_interface_client::RqdReportInterfaceClient};
use rand::rng;
use rand::seq::IndexedRandom;
use tokio::sync::RwLock;
use tonic::transport::Channel;
use tower::ServiceBuilder;
use tower::util::rng::HasherRng;
use tracing::info;

use super::retry::backoff::{ExponentialBackoffMaker, MakeBackoff};
use super::retry::backoff_policy::BackoffPolicy;
use super::retry::{Retry, RetryLayer};

pub(crate) struct ReportClient {
    config: GrpcConfig,
    refresh_at: RwLock<Option<SystemTime>>,
    client: RwLock<RqdReportInterfaceClient<Retry<BackoffPolicy, Channel>>>,
}

impl ReportClient {
    pub async fn build(config: &Config) -> Result<Self> {
        let should_refresh_connection = config.grpc.connection_expires_after
            > Duration::from_secs(0)
            && config.grpc.cuebot_endpoints.len() > 1;
        let refresh_at = should_refresh_connection
            .then(|| SystemTime::now().checked_add(config.grpc.connection_expires_after))
            .flatten();

        let (endpoint, client) = Self::connect(&config.grpc)?;
        Self::log_connection(refresh_at, &config.grpc.cuebot_endpoints, &endpoint);

        // Return the constructed client
        Ok(Self {
            config: config.grpc.clone(),
            client: RwLock::new(client),
            refresh_at: RwLock::new(refresh_at),
        })
    }

    fn log_connection(
        refresh_at: Option<SystemTime>,
        endpoints: &Vec<String>,
        connected_endpoint: &str,
    ) {
        let recycle_txt = match refresh_at {
            Some(next_time) => {
                let time_str: DateTime<Local> = next_time.into();
                format!("Expires at {}", time_str.format("%Y-%m-%d %H:%M:%S"))
            }
            None => "".to_string(),
        };
        info!(
            "Report client connecting to {} ({:?}). {}",
            connected_endpoint, endpoints, recycle_txt
        );
    }

    fn connect(
        config: &GrpcConfig,
    ) -> Result<(
        String,
        RqdReportInterfaceClient<Retry<BackoffPolicy, Channel>>,
    )> {
        let endpoint = Self::draw_endpoint(&config.cuebot_endpoints)?;
        let endpoint = if !endpoint.starts_with("http") {
            format!("http://{}", endpoint)
        } else {
            endpoint
        };
        let channel = tonic::transport::Channel::from_shared(endpoint.clone())
            .into_diagnostic()?
            .connect_lazy();

        // Use a backoff strategy to retry failed requests
        let backoff = ExponentialBackoffMaker::new(
            config.backoff_delay_min,
            config.backoff_delay_max,
            config.backoff_jitter_percentage,
            HasherRng::default(),
        )
        .into_diagnostic()?
        .make_backoff();

        // Requests will retry indefinitely
        let retry_policy = BackoffPolicy {
            attempts: None,
            backoff,
        };
        let retry_layer = RetryLayer::new(retry_policy);
        let channel = ServiceBuilder::new().layer(retry_layer).service(channel);

        Ok((endpoint, RqdReportInterfaceClient::new(channel)))
    }

    fn draw_endpoint(endpoints: &[String]) -> Result<String> {
        match endpoints.choose(&mut rng()) {
            Some(endpoint) => Ok(endpoint.clone()),
            None => Err(miette!("Invalid empty grpc endpoint configuration")),
        }
    }

    async fn get_client(&self) -> Result<RqdReportInterfaceClient<Retry<BackoffPolicy, Channel>>> {
        let refresh_at_lock = self.refresh_at.read().await;
        let refresh_at = *refresh_at_lock;
        drop(refresh_at_lock);
        match refresh_at {
            Some(expire_time) if SystemTime::now() >= expire_time => {
                info!("Report grpc connection expired. Reconnecting..");
                // Update connection
                let mut lock = self.client.write().await;
                let (endpoint, conn_lock) = Self::connect(&self.config)?;
                *lock = conn_lock;
                drop(lock);

                // Update next refresh_at
                let mut lock = self.refresh_at.write().await;
                let next_expire_time =
                    SystemTime::now().checked_add(self.config.connection_expires_after);
                *lock = next_expire_time;
                Self::log_connection(next_expire_time, &self.config.cuebot_endpoints, &endpoint);
                drop(lock);

                Ok(self.client.read().await.clone())
            }
            _ => Ok(self.client.read().await.clone()),
        }
    }
}

#[async_trait]
pub trait ReportInterface {
    async fn send_start_up_report(
        &self,
        render_host: pb::RenderHost,
        core_detail: pb::CoreDetail,
    ) -> Result<()>;
    async fn send_frame_complete_report(
        &self,
        host: pb::RenderHost,
        frame: pb::RunningFrameInfo,
        exit_status: u32,
        exit_signal: u32,
        run_time: u32,
    ) -> Result<()>;
    async fn send_host_report(&self, host_report: pb::HostReport) -> Result<()>;
}

#[async_trait]
impl ReportInterface for ReportClient {
    async fn send_start_up_report(
        &self,
        render_host: pb::RenderHost,
        core_detail: pb::CoreDetail,
    ) -> Result<()> {
        let request = pb::RqdReportRqdStartupRequest {
            boot_report: Some(pb::BootReport {
                host: Some(render_host),
                core_info: Some(core_detail),
            }),
        };
        self.get_client()
            .await?
            .report_rqd_startup(request)
            .await
            .into_diagnostic()
            .and(Ok(()))
    }

    async fn send_frame_complete_report(
        &self,
        render_host: pb::RenderHost,
        running_frame: pb::RunningFrameInfo,
        exit_status: u32,
        exit_signal: u32,
        run_time: u32,
    ) -> Result<()> {
        let request = pb::RqdReportRunningFrameCompletionRequest {
            frame_complete_report: Some(pb::FrameCompleteReport {
                host: Some(render_host),
                frame: Some(running_frame),
                exit_status: exit_status as i32,
                exit_signal: exit_signal as i32,
                run_time: run_time as i32,
            }),
        };
        self.get_client()
            .await?
            .report_running_frame_completion(request)
            .await
            .into_diagnostic()
            .and(Ok(()))
    }

    async fn send_host_report(&self, host_report: pb::HostReport) -> Result<()> {
        let request = pb::RqdReportStatusRequest {
            host_report: Some(host_report),
        };
        self.get_client()
            .await?
            .report_status(request)
            .await
            .into_diagnostic()
            .and(Ok(()))
    }
}
