use std::str::FromStr;

use miette::{miette, Context, IntoDiagnostic};
use structopt::StructOpt;
use tokio::signal::unix::{signal, SignalKind};
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};
use tracing_subscriber::{layer::SubscriberExt, reload};
use tracing_subscriber::{EnvFilter, Registry};

use crate::{
    cluster::{Cluster, ClusterFeed},
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
};

mod allocation;
mod cluster;
mod cluster_key;
mod config;
mod dao;
mod host_cache;
mod metrics;
mod models;
mod pgpool;
mod pipeline;

// scheduler --facility eat --alloc_tags=show:tag,show:tag,show:tag --manual_tags=tag1,tag2
#[derive(StructOpt, Debug)]
pub struct JobQueueCli {
    #[structopt(long, short = "f", long_help = "Facility code to run on")]
    facility: Option<String>,

    #[structopt(
        long,
        short = "a",
        long_help = "A list of show:tag entries associated to an allocation. (eg. show1:general)."
    )]
    alloc_tags: Vec<ColonSeparatedList>,

    #[structopt(
        long,
        short = "t",
        long_help = "A list of tags not associated with an allocation."
    )]
    manual_tags: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct ColonSeparatedList(pub String, pub String);

impl FromStr for ColonSeparatedList {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let parts: Vec<&str> = s.split(":").map(|v| v.trim()).collect();
        if parts.len() != 2 {
            return Err(format!("Invalid format: expected 'show:tag', got '{}'", s));
        }
        Ok(ColonSeparatedList(
            parts[0].to_string(),
            parts[1].to_string(),
        ))
    }
}

impl JobQueueCli {
    async fn run(&self) -> miette::Result<()> {
        // Merge CLI args with config, CLI takes precedence
        let facility = if self.facility.is_some() {
            self.facility.clone()
        } else {
            CONFIG.scheduler.facility.clone()
        };

        let alloc_tags = if !self.alloc_tags.is_empty() {
            // CLI args provided, use them
            self.alloc_tags.clone()
        } else {
            // Use config values
            CONFIG
                .scheduler
                .alloc_tags
                .iter()
                .map(|at| ColonSeparatedList(at.show.clone(), at.tag.clone()))
                .collect()
        };

        let manual_tags = if !self.manual_tags.is_empty() {
            // CLI args provided, use them
            self.manual_tags.clone()
        } else {
            // Use config values
            CONFIG.scheduler.manual_tags.clone()
        };

        // Lookup facility_id from facility name
        let facility_id = match &facility {
            Some(facility) => Some(
                cluster::get_facility_id(facility)
                    .await
                    .wrap_err("Invalid facility name")?,
            ),
            None => None,
        };

        let mut clusters = Vec::new();

        if let Some(facility_id) = &facility_id {
            // Build Cluster::ComposedKey for each alloc_tag (show:tag format)
            for alloc_tag in &alloc_tags {
                let show_id = cluster::get_show_id(&alloc_tag.0)
                    .await
                    .wrap_err("Could not find show {}.")?;
                clusters.push(Cluster::ComposedKey(ClusterKey {
                    facility_id: facility_id.clone(),
                    show_id,
                    tag: Tag {
                        name: alloc_tag.1.clone(),
                        ttype: TagType::Alloc,
                    },
                }));
            }
        } else if !alloc_tags.is_empty() {
            Err(miette!("Alloc tag requires a valid facility"))?
        }

        // Build Cluster::TagsKey for manual_tags
        if !manual_tags.is_empty() {
            clusters.push(Cluster::TagsKey(
                manual_tags
                    .iter()
                    .map(|name| Tag {
                        name: name.clone(),
                        ttype: TagType::Manual,
                    })
                    .collect(),
            ));
        }
        let cluster_feed = if alloc_tags.is_empty() && manual_tags.is_empty() {
            ClusterFeed::load_all(&facility_id).await?
        } else {
            ClusterFeed::load_from_clusters(clusters)
        };

        pipeline::run(cluster_feed).await
    }
}

fn main() -> miette::Result<()> {
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

    tracing::subscriber::set_global_default(subs).expect("Unable to set global subscriber");

    // Start Prometheus metrics HTTP server in background
    let metrics_addr = "0.0.0.0:9090";
    tokio::spawn(async move {
        if let Err(e) = metrics::start_server(metrics_addr).await {
            tracing::error!("Metrics server failed: {}", e);
        }
    });

    // Watch for sigusr1, when received toggle between info/debug levels
    tokio::spawn(async move {
        let mut sigusr1 =
            signal(SignalKind::user_defined1()).expect("Failed to register signal listener");
        let mut is_info = CONFIG.logging.level.to_lowercase() == "info";
        loop {
            sigusr1.recv().await;

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
    });

    let opts = JobQueueCli::from_args();
    let result = opts.run().await;

    actix::System::current().stop();

    result
}
