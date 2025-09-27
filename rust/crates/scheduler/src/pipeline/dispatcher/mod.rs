pub mod actor;
pub mod error;
mod frame_set;
pub mod messages;

use crate::{
    dao::{FrameDao, HostDao},
    models::{CoreSize, DispatchFrame, DispatchLayer, Host, VirtualProc},
    pipeline::dispatcher::{
        error::{DispatchError, VirtualProcError},
        frame_set::FrameSet,
    },
};
use bytesize::{ByteSize, MIB};
use futures::FutureExt;
use miette::{Context, IntoDiagnostic, Result, miette};
use opencue_proto::{
    host::ThreadMode,
    rqd::{RqdStaticLaunchFrameRequest, RunFrame, rqd_interface_client::RqdInterfaceClient},
};
use sqlx::{Postgres, Transaction};
use std::{collections::HashMap, sync::Arc};
use tonic::transport::Channel;
use tracing::{debug, error, info};
use uuid::Uuid;

// Actor and singleton support
use actix::{Actor, Addr};
pub use actor::RqdDispatcherService;
use tokio::sync::OnceCell;

static RQD_DISPATCHER: OnceCell<Addr<RqdDispatcherService>> = OnceCell::const_new();

/// RQD dispatcher responsible for dispatching frames to render hosts.
///
/// The dispatcher handles:
/// - Frame-to-host matching and resource allocation
/// - gRPC communication with RQD instances
/// - Resource consumption tracking and validation
/// - Frame command preparation and execution setup
#[derive(Clone)]
pub struct RqdDispatcher {
    frame_dao: Arc<FrameDao>,
    host_dao: Arc<HostDao>,
    dry_run_mode: bool,
}

/// Singleton getter for the RQD dispatcher service
///
/// Creates and returns a singleton instance of the RqdDispatcherService actor.
/// The service is initialized with configuration from CONFIG on first access.
///
/// # Usage Example
/// ```rust,no_run
/// use crate::pipeline::dispatcher::{rqd_dispatcher_service, messages::DispatchLayer};
/// use crate::models::{DispatchLayer as ModelDispatchLayer, Host};
///
/// async fn dispatch_example() -> miette::Result<()> {
///     let dispatcher = rqd_dispatcher_service().await?;
///
///     let message = DispatchLayer {
///         layer: my_layer,
///         host: my_host,
///         transaction_id: "tx-123".to_string(),
///     };
///
///     match dispatcher.send(message).await {
///         Ok(Ok(result)) => {
///             println!("Dispatched {} frames", result.dispatched_frames.len());
///         }
///         Ok(Err(e)) => println!("Dispatch error: {}", e),
///         Err(e) => println!("Actor mailbox error: {}", e),
///     }
///
///     Ok(())
/// }
/// ```
pub async fn rqd_dispatcher_service() -> Result<Addr<RqdDispatcherService>, miette::Error> {
    RQD_DISPATCHER
        .get_or_try_init(|| async {
            use crate::{
                config::CONFIG,
                dao::{FrameDao, HostDao},
            };

            let frame_dao = Arc::new(FrameDao::from_config(&CONFIG.database).await?);
            let host_dao = Arc::new(HostDao::from_config(&CONFIG.database).await?);

            let service =
                RqdDispatcherService::new(frame_dao, host_dao, CONFIG.rqd.dry_run_mode).await?;

            Ok(service.start())
        })
        .await
        .cloned()
}
