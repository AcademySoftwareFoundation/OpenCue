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

//! `cueadmin`: OpenCue administration tool.

use std::process::ExitCode;

use clap::Parser;
use miette::{IntoDiagnostic, Result};
use tracing_subscriber::EnvFilter;

use crate::cli::Cli;
use crate::client::Cuebot;
use crate::commands::Context;
use crate::config::Config;

mod cli;
mod client;
mod commands;
mod config;
mod criteria;
mod format;
mod output;

fn main() -> ExitCode {
    let cli = Cli::parse();
    init_logging(cli.verbose);

    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(e) => {
            eprintln!("Error: failed to start the async runtime: {e}");
            return ExitCode::FAILURE;
        }
    };
    match runtime.block_on(run(cli)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(report) => {
            eprintln!("{report:?}");
            ExitCode::FAILURE
        }
    }
}

async fn run(cli: Cli) -> Result<()> {
    // With --server the file only supplies tuning values, so a broken file shouldn't block us.
    let config = match Config::load() {
        Ok(config) => config,
        Err(e) if !cli.server.is_empty() => {
            tracing::warn!("ignoring opencue config, using defaults: {e:?}");
            Config::default()
        }
        Err(e) => return Err(e),
    };
    let hosts = config.resolve_hosts(
        &cli.server,
        cli.facility.as_deref(),
        std::env::var("CUEBOT_HOSTS").ok().as_deref(),
        std::env::var("CUEBOT_FACILITY").ok().as_deref(),
    )?;
    let ctx = Context {
        cuebot: Cuebot::connect(&hosts, &config).await?,
        force: cli.force,
    };
    commands::run(&ctx, cli.command).await
}

fn init_logging(verbose: bool) {
    let default = if verbose { "cueadmin=debug" } else { "warn" };
    let filter = EnvFilter::try_from_env("CUEADMIN_LOG")
        .or_else(|_| EnvFilter::try_new(default))
        .into_diagnostic();
    if let Ok(filter) = filter {
        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_writer(std::io::stderr)
            .with_target(false)
            .without_time()
            .init();
    }
}
