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

use miette::{Context, IntoDiagnostic};
use structopt::StructOpt;
#[cfg(unix)]
use tokio::signal::unix::{signal, SignalKind};
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};
use tracing_subscriber::{layer::SubscriberExt, reload};
use tracing_subscriber::{EnvFilter, Registry};

use crate::{cluster::ClusterFeed, config::CONFIG};

mod accounting;
mod cluster;
mod cluster_key;
mod config;
mod dao;
mod host_cache;
mod metrics;
mod models;
mod pgpool;
mod pipeline;

// scheduler --facility eat
#[derive(StructOpt, Debug)]
pub struct JobQueueCli {
    #[structopt(long, short = "f", long_help = "Facility code to run on")]
    facility: Option<String>,

    #[structopt(
        long,
        short = "i",
        long_help = "A list of tags to ignore when loading clusters."
    )]
    ignore_tags: Vec<String>,
}

impl JobQueueCli {
    /// Merge CLI args with config values, where CLI takes precedence.
    ///
    /// For each field, if a CLI argument was provided it is used; otherwise the
    /// value falls back to the corresponding entry in [`CONFIG.scheduler`].
    ///
    /// # Returns
    ///
    /// A tuple of `(facility, ignore_tags)`:
    /// - `facility`    – Optional facility code (e.g. `"eat"`); scopes this
    ///   instance to one facility's scheduler-managed clusters.
    /// - `ignore_tags` – Tags to exclude when loading clusters.
    ///
    /// Show ownership itself is not configured here - it is driven entirely by
    /// the `show.b_scheduler_managed` DB column.
    fn resolve_config(&self) -> (Option<String>, Vec<String>) {
        let facility = if self.facility.is_some() {
            self.facility.clone()
        } else {
            CONFIG.scheduler.facility.clone()
        };

        let ignore_tags = if !self.ignore_tags.is_empty() {
            self.ignore_tags.clone()
        } else {
            CONFIG.scheduler.ignore_tags.clone()
        };

        (facility, ignore_tags)
    }

    async fn run(&self) -> miette::Result<()> {
        let (facility, ignore_tags) = self.resolve_config();

        // Lookup facility_id from facility name
        let facility_id = match &facility {
            Some(facility) => Some(
                cluster::get_facility_id(facility)
                    .await
                    .wrap_err("Invalid facility name")?,
            ),
            None => None,
        };

        let builder = match facility_id {
            Some(id) => ClusterFeed::facility(id),
            None => ClusterFeed::no_facility(),
        };
        let cluster_feed = builder.with_ignore_tags(ignore_tags).build().await?;

        pipeline::run(cluster_feed).await
    }
}

fn main() -> miette::Result<()> {
    let _sentry_guard = sentry::init(sentry::ClientOptions {
        dsn: CONFIG.sentry_dsn.as_deref().and_then(|s| {
            if s.is_empty() {
                None
            } else {
                match s.parse() {
                    Ok(dsn) => Some(dsn),
                    Err(err) => {
                        eprintln!("Invalid Sentry dsn. Sentry is disabled. {}", err);
                        None
                    }
                }
            }
        }),
        release: sentry::release_name!(),
        ..Default::default()
    });

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(CONFIG.queue.worker_threads)
        .enable_all()
        .build()
        .into_diagnostic()?;

    // Spawn the actor system in the background
    let actor_system = actix::System::with_tokio_rt(|| runtime);

    actor_system.block_on(async_main())
}

async fn async_main() -> miette::Result<()> {
    let log_level = CONFIG.logging.level.as_str().to_lowercase();

    // Use EnvFilter to suppress sqlx logs (set to warn so only warnings/errors show)
    let filter = EnvFilter::new(log_level);
    let (filter, reload_handle) = reload::Layer::new(filter);

    let stdout_log = tracing_subscriber::fmt::layer().pretty();
    let subs = Registry::default().with(stdout_log).with(filter);

    let file_appender_layer = if CONFIG.logging.file_appender {
        let file_appender = RollingFileAppenderBase::new(
            CONFIG.logging.path.clone(),
            RollingConditionBase::new().max_size(1024 * 1024),
            7,
        )
        .expect("Failed to create appender");
        let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);
        Some(tracing_subscriber::fmt::layer().with_writer(non_blocking))
    } else {
        None
    };
    let subs = subs.with(file_appender_layer);

    let sentry_layer = sentry::integrations::tracing::layer().event_filter(|metadata| {
        // Register sqlx WARN messages as Sentry issues (events) instead of breadcrumbs
        if (metadata.target().starts_with("sqlx") && *metadata.level() == tracing::Level::WARN)
            || metadata.level() <= &tracing::Level::ERROR
        {
            sentry::integrations::tracing::EventFilter::Event
        } else {
            sentry::integrations::tracing::EventFilter::Breadcrumb
        }
    });
    let subs = subs.with(sentry_layer);

    tracing::subscriber::set_global_default(subs).expect("Unable to set global subscriber");

    // Start Prometheus metrics HTTP server in background
    let metrics_addr = format!("0.0.0.0:{}", CONFIG.queue.metrics_port);
    tokio::spawn(async move {
        if let Err(e) = metrics::start_server(&metrics_addr).await {
            tracing::error!("Metrics server failed: {}", e);
        }
    });

    // Watch for sigusr1 and sigusr2, when received toggle between info/debug levels
    // Note: Unix signals (SIGUSR1/SIGUSR2) are not available on Windows
    #[cfg(unix)]
    tokio::spawn(async move {
        let mut sigusr1 =
            signal(SignalKind::user_defined1()).expect("Failed to register signal listener");
        let mut sigusr2 =
            signal(SignalKind::user_defined2()).expect("Failed to register signal listener");
        let mut is_info = CONFIG.logging.level.to_lowercase() == "info";
        loop {
            tokio::select! {
                _ =
                sigusr1.recv() => {

                    // Toggle log between info and DEBUG (keep sqlx at info so it doesn't show up)
                    is_info = !is_info;
                    let new_filter = if is_info {
                        EnvFilter::new("info,sqlx=info")
                    } else {
                        EnvFilter::new("debug,sqlx=info")
                    };
                    reload_handle
                        .modify(|filter| {
                            *filter = new_filter;
                        })
                        .ok();
                }
                _ =
                sigusr2.recv() => {

                    // Toggle log between info and DEBUG (keep sqlx at info so it doesn't show up)
                    is_info = !is_info;
                    let new_filter = if is_info {
                        EnvFilter::new("info,sqlx=info")
                    } else {
                        EnvFilter::new("debug,sqlx=debug")
                    };
                    reload_handle
                        .modify(|filter| {
                            *filter = new_filter;
                        })
                        .ok();
                }
            }
        }
    });

    // Log which host booking strategy is active so operators can confirm the
    // running configuration without inspecting the YAML.
    match &CONFIG.queue.host_booking_strategy {
        config::HostBookingStrategy::Saturation {
            core_saturation,
            memory_saturation,
        } => tracing::info!(
            core_saturation,
            memory_saturation,
            "Host booking strategy: Saturation (first-fit)"
        ),
        config::HostBookingStrategy::Epvm {
            weights,
            max_candidates,
        } => tracing::info!(
            max_candidates,
            weight.cores = weights.cores,
            weight.mem = weights.mem,
            weight.gpus = weights.gpus,
            weight.gpu_mem = weights.gpu_mem,
            weight.gpu_count_reservation = weights.gpu_count_reservation,
            weight.gpu_mem_reservation = weights.gpu_mem_reservation,
            "Host booking strategy: E-PVM (lowest-stranding score)"
        ),
    }

    let opts = JobQueueCli::from_args();
    let result = opts.run().await;

    actix::System::current().stop();

    result
}
