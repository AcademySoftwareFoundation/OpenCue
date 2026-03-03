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

use miette::{miette, Context, IntoDiagnostic};
use structopt::StructOpt;
use tokio::signal::unix::{signal, SignalKind};
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};
use tracing_subscriber::{layer::SubscriberExt, reload};
use tracing_subscriber::{EnvFilter, Registry};

use crate::config::{AllocTag, ManualTags};
use crate::{
    cluster::{Cluster, ClusterFeed},
    cluster_key::{Tag, TagType},
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
        short = "s",
        long_help = "A list of show names to be scheduled entirely."
    )]
    entire_shows: Vec<String>,

    #[structopt(
        long,
        short = "a",
        long_help = "A list of show:tag entries associated to an allocation. (eg. show1:general)."
    )]
    alloc_tags: Vec<ColonSeparatedList>,

    #[structopt(
        long,
        short = "t",
        long_help = "A list of show and tags not associated with an allocation. (eg. show1:tag1,tag2,tag3)"
    )]
    manual_tags: Vec<ColonSeparatedList>,

    #[structopt(
        long,
        short = "i",
        long_help = "A list of tags to ignore when loading clusters."
    )]
    ignore_tags: Vec<String>,
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

impl From<ColonSeparatedList> for AllocTag {
    fn from(value: ColonSeparatedList) -> Self {
        AllocTag {
            show: value.0,
            tag: value.1,
        }
    }
}

impl JobQueueCli {
    /// Merge CLI args with config values, where CLI takes precedence.
    ///
    /// For each field, if a CLI argument was provided it is used; otherwise the
    /// value falls back to the corresponding entry in [`CONFIG.scheduler`].
    ///
    /// # Returns
    ///
    /// A tuple of `(facility, alloc_tags, manual_tags, ignore_tags)`:
    /// - `facility`      – Optional facility code (e.g. `"eat"`).
    /// - `entire_shows`  – Name of shows to be completely scheduled (e.g. `show1`).
    /// - `alloc_tags`    – Show/tag pairs tied to an allocation (e.g. `show1:general`).
    /// - `manual_tags`   – Free-form tags not associated with an allocation.
    /// - `ignore_tags`   – Tags to exclude when loading clusters.
    #[allow(clippy::type_complexity)]
    fn resolve_config(
        &self,
    ) -> (
        Option<String>,
        Vec<String>,
        Vec<AllocTag>,
        Vec<ManualTags>,
        Vec<String>,
    ) {
        let facility = if self.facility.is_some() {
            self.facility.clone()
        } else {
            CONFIG.scheduler.facility.clone()
        };

        let entire_shows: Vec<String> = if !self.entire_shows.is_empty() {
            self.entire_shows.clone()
        } else {
            CONFIG.scheduler.entire_shows.clone()
        };

        let alloc_tags: Vec<AllocTag> = if !self.alloc_tags.is_empty() {
            self.alloc_tags
                .clone()
                .into_iter()
                .map(|item| item.into())
                .collect()
        } else {
            CONFIG.scheduler.alloc_tags.clone()
        };

        let manual_tags = if !self.manual_tags.is_empty() {
            self.manual_tags
                .clone()
                .into_iter()
                .map(|item| ManualTags {
                    show: item.0,
                    tags: item.1.split(",").map(|t| t.to_string()).collect(),
                })
                .collect()
        } else {
            CONFIG.scheduler.manual_tags.clone()
        };

        let ignore_tags = if !self.ignore_tags.is_empty() {
            self.ignore_tags.clone()
        } else {
            CONFIG.scheduler.ignore_tags.clone()
        };

        (facility, entire_shows, alloc_tags, manual_tags, ignore_tags)
    }

    async fn run(&self) -> miette::Result<()> {
        let (facility, entire_shows, alloc_tags, manual_tags, ignore_tags) = self.resolve_config();

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
                let show_id = cluster::get_show_id(&alloc_tag.show)
                    .await
                    .wrap_err(format!("Could not find show {}.", alloc_tag.show))?;
                clusters.push(Cluster::single_tag(
                    *facility_id,
                    show_id,
                    Tag {
                        name: alloc_tag.tag.clone(),
                        ttype: TagType::Alloc,
                    },
                ));
            }

            // Build Cluster::TagsKey for manual_tags
            for manual_tag in &manual_tags {
                let show_id = cluster::get_show_id(&manual_tag.show)
                    .await
                    .wrap_err(format!("Could not find show {}.", manual_tag.show))?;
                clusters.push(Cluster::multiple_tag(
                    *facility_id,
                    show_id,
                    manual_tag
                        .tags
                        .iter()
                        .map(|name| Tag {
                            name: name.clone(),
                            ttype: TagType::Manual,
                        })
                        .collect(),
                ));
            }
        } else if !alloc_tags.is_empty() {
            Err(miette!("Alloc tag requires a valid facility"))?
        } else if !manual_tags.is_empty() {
            Err(miette!("Manual tag requires a valid facility"))?
        }

        let builder = match facility_id {
            Some(id) => ClusterFeed::facility(id),
            None => ClusterFeed::no_facility(),
        };
        let cluster_feed = builder
            .with_ignore_tags(ignore_tags)
            .with_clusters(clusters)
            .with_entire_shows(entire_shows)
            .build()
            .await?;

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
    let metrics_addr = format!("0.0.0.0:{}", CONFIG.queue.metrics_port);
    tokio::spawn(async move {
        if let Err(e) = metrics::start_server(&metrics_addr).await {
            tracing::error!("Metrics server failed: {}", e);
        }
    });

    // Watch for sigusr1 and sigusr2, when received toggle between info/debug levels
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

    let opts = JobQueueCli::from_args();
    let result = opts.run().await;

    actix::System::current().stop();

    result
}
