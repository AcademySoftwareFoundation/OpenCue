use std::{
    str::FromStr,
    sync::{Arc, Mutex},
};

use config::config::Config;
use miette::IntoDiagnostic;
use monitor::system::MachineMonitor;
use report_client::ReportClient;
use running_frame::RunningFrameCache;
use sysinfo::{Disks, MemoryRefreshKind, RefreshKind, System};
use tracing::error;
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

mod config;
mod monitor;
mod report_client;
mod running_frame;
mod servant;

#[tokio::main(flavor = "multi_thread", worker_threads = 8)]
async fn main() -> miette::Result<()> {
    let config = Config::load()?;

    let log_level =
        tracing::Level::from_str(&config.logging.level.as_str()).expect("Invalid log level");
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

    let running_frame_cache = Arc::new(RunningFrameCache::init());
    // Initialize cuebot client
    let report_client = Arc::new(ReportClient::build(&config).await?);

    // Make clones for the async block
    let config_clone = config.clone();
    let running_frame_cache_clone = Arc::clone(&running_frame_cache);

    // Initialize sysinfo collectors
    let sysinfo = Arc::new(Mutex::new(System::new_with_specifics(
        RefreshKind::nothing().with_memory(MemoryRefreshKind::everything()),
    )));
    let diskinfo = Arc::new(Mutex::new(Disks::new_with_refreshed_list()));

    // Initialize rqd machine monitor
    let machine_monitor = Arc::new(MachineMonitor::init(
        &config_clone,
        report_client,
        Arc::clone(&running_frame_cache_clone),
        sysinfo,
        diskinfo,
    )?);
    let mm_clone = Arc::clone(&machine_monitor);
    tokio::spawn(async move {
        if let Err(e) = machine_monitor.start().await {
            panic!("MachineMonitor loop crashed. {e}")
        }
    });

    // Initialize rqd grpc servant
    servant::serve(config, Arc::clone(&running_frame_cache), mm_clone)
        .await
        .into_diagnostic()
}
