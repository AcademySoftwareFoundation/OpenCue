use std::str::FromStr;

use miette::{Context, IntoDiagnostic, miette};
use structopt::StructOpt;
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

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
        // Lookup facility_id from facility name
        let facility_id = match &self.facility {
            Some(facility) => Some(
                cluster::get_facility_id(facility)
                    .await
                    .wrap_err("Invalid facility name")?,
            ),
            None => None,
        };

        let mut clusters = Vec::new();

        if let Some(facility_id) = facility_id {
            // Build Cluster::ComposedKey for each alloc_tag (show:tag format)
            for alloc_tag in &self.alloc_tags {
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
        } else if !self.alloc_tags.is_empty() {
            Err(miette!("Alloc tag requires a valid facility"))?
        }

        // Build Cluster::TagsKey for manual_tags
        if !self.manual_tags.is_empty() {
            clusters.push(Cluster::TagsKey(
                self.manual_tags
                    .iter()
                    .map(|name| Tag {
                        name: name.clone(),
                        ttype: TagType::Manual,
                    })
                    .collect(),
            ));
        }
        let cluster_feed = if self.alloc_tags.is_empty() && self.manual_tags.is_empty() {
            ClusterFeed::load_all(false, &self.facility).await?
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

    let opts = JobQueueCli::from_args();
    let result = opts.run().await;

    actix::System::current().stop();

    result
}
