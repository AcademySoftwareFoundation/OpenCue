use std::sync::Arc;
use std::time::{Duration, SystemTime};

use crate::config::CONFIG;
use async_trait::async_trait;
use chrono::{DateTime, Local};
use miette::{IntoDiagnostic, Result, miette};
use opencue_proto::report::{self as pb, rqd_report_interface_client::RqdReportInterfaceClient};
use rand::rng;
use rand::seq::IndexedRandom;
use tokio::sync::{OnceCell, RwLock};
use tonic::transport::Channel;
use tower::ServiceBuilder;
use tower::util::rng::HasherRng;
use tracing::info;

use super::retry::backoff::{ExponentialBackoffMaker, MakeBackoff};
use super::retry::backoff_policy::BackoffPolicy;
use super::retry::{Retry, RetryLayer};

pub(crate) struct ReportClient {
    refresh_at: RwLock<Option<SystemTime>>,
    client: RwLock<RqdReportInterfaceClient<Retry<BackoffPolicy, Channel>>>,
}

static REPORT_CLIENT: OnceCell<Arc<ReportClient>> = OnceCell::const_new();

/// Gets or initializes the singleton instance of the ReportClient.
///
/// This function returns a reference-counted pointer to the global ReportClient instance.
/// The client is initialized lazily on first access. If the client is already initialized,
/// this returns the existing instance. Otherwise, it creates a new client by calling
/// `ReportClient::build()`.
///
/// # Returns
///
/// Returns `Ok(Arc<ReportClient>)` on success, or an error if the client fails to initialize.
///
/// # Errors
///
/// This function will return an error if:
/// - The gRPC endpoint configuration is invalid or empty
/// - The connection to the cuebot server cannot be established
pub async fn instance() -> Result<Arc<ReportClient>> {
    REPORT_CLIENT
        .get_or_try_init(|| async { Ok(Arc::new(ReportClient::build().await?)) })
        .await
        .map(Arc::clone)
}

impl ReportClient {
    async fn build() -> Result<Self> {
        let should_refresh_connection = CONFIG.grpc.connection_expires_after
            > Duration::from_secs(0)
            && CONFIG.grpc.cuebot_endpoints.len() > 1;
        let refresh_at = should_refresh_connection
            .then(|| SystemTime::now().checked_add(CONFIG.grpc.connection_expires_after))
            .flatten();

        let (endpoint, client) = Self::connect()?;
        Self::log_connection(refresh_at, &CONFIG.grpc.cuebot_endpoints, &endpoint);

        // Return the constructed client
        Ok(Self {
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

    fn connect() -> Result<(
        String,
        RqdReportInterfaceClient<Retry<BackoffPolicy, Channel>>,
    )> {
        let endpoint = Self::draw_endpoint(&CONFIG.grpc.cuebot_endpoints)?;
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
            CONFIG.grpc.backoff_delay_min,
            CONFIG.grpc.backoff_delay_max,
            CONFIG.grpc.backoff_jitter_percentage,
            HasherRng::default(),
        )
        .into_diagnostic()?
        .make_backoff();

        // Requests will retry indefinitely
        let retry_policy = BackoffPolicy {
            attempts: Some(CONFIG.grpc.backoff_retry_attempts),
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
                let (endpoint, conn_lock) = Self::connect()?;
                *lock = conn_lock;
                drop(lock);

                // Update next refresh_at
                let mut lock = self.refresh_at.write().await;
                let next_expire_time =
                    SystemTime::now().checked_add(CONFIG.grpc.connection_expires_after);
                *lock = next_expire_time;
                Self::log_connection(next_expire_time, &CONFIG.grpc.cuebot_endpoints, &endpoint);
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
