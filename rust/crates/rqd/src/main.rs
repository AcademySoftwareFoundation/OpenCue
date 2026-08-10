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

use std::str::FromStr;

use miette::IntoDiagnostic;
use tokio::{select, sync::oneshot};
use tracing::{error, warn};
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

#[cfg(unix)]
use crate::frame::manager;
use crate::{
    config::CONFIG,
    system::{capabilities, machine},
};

mod config;
mod frame;
mod report;
mod servant;
mod system;

fn main() -> miette::Result<()> {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(CONFIG.machine.worker_threads)
        .enable_all()
        .build()
        .into_diagnostic()?;

    runtime.block_on(async_main())
}

async fn async_main() -> miette::Result<()> {
    // Ensure provisioned paths (snapshots, machine temp) exist before any
    // subsystem touches them.
    CONFIG.setup()?;

    let log_level =
        tracing::Level::from_str(CONFIG.logging.level.as_str()).expect("Invalid log level");
    let log_builder = tracing_subscriber::fmt()
        .with_timer(tracing_subscriber::fmt::time::SystemTime)
        .pretty()
        .with_max_level(log_level);
    if CONFIG.logging.file_appender {
        let file_appender = RollingFileAppenderBase::new(
            CONFIG.logging.path.clone(),
            RollingConditionBase::new().max_size(1024 * 1024),
            7,
        )
        .expect("Failed to create appender");
        let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);
        log_builder.with_writer(non_blocking).init();
    } else {
        log_builder.init();
    }

    // Compile the log_exit_status_rules once now that logging is up, so an operator's typo in a
    // rule's regex surfaces as a single startup warning instead of repeating on every failed
    // frame (and no frame later pays to recompile them).
    let _ = CONFIG.runner.compiled_exit_status_rules();

    // Fail fast if the config requires elevated privileges the process does not hold,
    // instead of letting every frame fail later with an opaque error.
    capabilities::preflight(&CONFIG.runner)?;

    // Start a channel for communitating when machine_monitor fully started
    let (tx, rx) = oneshot::channel::<()>();

    // Spawn machine monitor on a new task to prevent it from locking the main task
    let machine_monitor_handle = {
        let mm = machine::instance().await?;
        tokio::spawn(async move { mm.start(tx).await })
    };
    // Await for the confirmation machine_monitor has fully initialized
    let _machine_monitor_started = rx.await;

    // Recover frames that survived an RQD restart. Frames run in their own session
    // (setsid at spawn) so they are not killed alongside RQD; their exit status is
    // recovered from the exit file written by the frame's entrypoint wrapper.
    //
    // Note for Linux deployments under systemd: the unit must set `KillMode=process`
    // (see resources/openrqd.service). With the default `control-group` kill mode,
    // systemd kills every process in the unit's cgroup on stop/restart — including
    // the frames — regardless of their session or process group.
    #[cfg(unix)]
    if let Err(err) = manager::instance().await?.recover_snapshots().await {
        warn!("Failed to recover frames from snapshot: {}", err);
    };

    // Initialize rqd grpc servant
    let machine_manager = machine::instance().await?;
    let servant_handle = servant::serve(machine_manager.clone());

    // Race machine_monitor and servant futures
    select! {
        machine_monitor_result = machine_monitor_handle => {
            if let Err(err) = machine_monitor_result {
                error!("Machine monitor crashed. {err}");
            }
        }
        servant_handle_result = servant_handle => {
            machine_manager.interrupt().await;
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
