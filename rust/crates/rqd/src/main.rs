use std::{str::FromStr, sync::Arc};

use config::Config;
use frame::manager::FrameManager;
use miette::IntoDiagnostic;
use report::report_client::ReportClient;
use system::machine::MachineMonitor;
use tokio::{select, sync::oneshot};
use tracing::{error, warn};
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

mod config;
mod frame;
mod report;
mod servant;
mod system;

fn main() -> miette::Result<()> {
    let config = Config::load()?;

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(config.machine.worker_threads)
        .enable_all()
        .build()
        .into_diagnostic()?;

    runtime.block_on(async_main(config))
}

async fn async_main(config: Config) -> miette::Result<()> {
    let log_level =
        tracing::Level::from_str(config.logging.level.as_str()).expect("Invalid log level");
    let log_builder = tracing_subscriber::fmt()
        .with_timer(tracing_subscriber::fmt::time::SystemTime)
        .pretty()
        .with_max_level(log_level);
    if config.logging.file_appender {
        let file_appender = RollingFileAppenderBase::new(
            config.logging.path.clone(),
            RollingConditionBase::new().max_size(1024 * 1024),
            7,
        )
        .expect("Failed to create appender");
        let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);
        log_builder.with_writer(non_blocking).init();
    } else {
        log_builder.init();
    }

    // Initialize cuebot client
    let report_client = Arc::new(ReportClient::build(&config).await?);

    // Make clones for the async block
    let config_clone = config.clone();

    // Initialize rqd machine monitor
    let machine_monitor = Arc::new(MachineMonitor::init(&config_clone, report_client)?);
    let mm_clone = Arc::clone(&machine_monitor);
    let mm_clone2 = Arc::clone(&machine_monitor);

    // Initialize frame manager
    let frame_manager = Arc::new(FrameManager {
        config: config.clone(),
        machine: mm_clone.clone(),
    });

    let (tx, rx) = oneshot::channel::<()>();

    // Spawn machine monitor on a new task to prevent it from locking the main task
    let machine_monitor_handle = {
        let mm = Arc::clone(&machine_monitor);
        tokio::spawn(async move { mm.start(tx).await })
    };
    // Await for the confirmation machine_monitor has fully initialized
    let _machine_monitor_started = rx.await;

    // Recovering frames is unstable on linux. Launched frames are somehow still bound
    // to the rqd process and receive a kill signal when rqd stops
    #[cfg(target_os = "macos")]
    if let Err(err) = frame_manager.recover_snapshots().await {
        warn!("Failed to recover frames from snapshot: {}", err);
    };

    // Initialize rqd grpc servant
    let servant_handle = servant::serve(config, mm_clone, frame_manager);

    // Race machine_monitor and servant futures
    select! {
        machine_monitor_result = machine_monitor_handle => {
            if let Err(err) = machine_monitor_result {
                error!("Machine monitor crashed. {err}");
            }
        }
        servant_handle_result = servant_handle => {
            mm_clone2.interrupt().await;
            if let Err(err) = servant_handle_result {
                error!("Rqd servant crashed. {err}");
            }
        }
    };
    Ok(())
}

// To launch a process in a different process group in Linux, a binary (or executable) needs to have the following capabilities:
// 1. **CAP_SYS_ADMIN**: This capability allows the process to perform a variety of administrative tasks, including creating and managing process groups.
// 2. **CAP_SETGID**: This capability allows the process to change the group ID of the process, which is necessary when launching a process in a different group.
// 3. **CAP_SETUID**: This capability allows the process to change the user ID of the process, which may be needed if the new process requires different user permissions.
// 4. **CAP_CHOWN**: This capability allows changing the ownership of files, which can be relevant if the new process needs to access specific resources.
// Having these capabilities enables the binary to effectively manage and launch processes in different groups as required.
