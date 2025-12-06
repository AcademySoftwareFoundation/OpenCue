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

//! OpenCue Monitoring Indexer
//!
//! This service consumes monitoring events from Kafka topics and indexes them
//! into Elasticsearch for historical analysis and querying.

mod config;
mod consumer;
mod elasticsearch;
mod error;

use clap::Parser;
use tracing::{info, Level};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

use crate::config::Config;
use crate::consumer::EventConsumer;
use crate::elasticsearch::ElasticsearchClient;

#[derive(Parser, Debug)]
#[command(name = "monitoring-indexer")]
#[command(about = "OpenCue monitoring event indexer - indexes events from Kafka to Elasticsearch")]
#[command(version)]
struct Args {
    /// Path to configuration file
    #[arg(short, long, env = "INDEXER_CONFIG")]
    config: Option<String>,

    /// Kafka bootstrap servers
    #[arg(long, env = "KAFKA_BOOTSTRAP_SERVERS", default_value = "localhost:9092")]
    kafka_servers: String,

    /// Kafka consumer group ID
    #[arg(long, env = "KAFKA_GROUP_ID", default_value = "opencue-monitoring-indexer")]
    kafka_group_id: String,

    /// Elasticsearch URL
    #[arg(long, env = "ELASTICSEARCH_URL", default_value = "http://localhost:9200")]
    elasticsearch_url: String,

    /// Elasticsearch index prefix
    #[arg(long, env = "ELASTICSEARCH_INDEX_PREFIX", default_value = "opencue")]
    index_prefix: String,

    /// Log level
    #[arg(long, env = "LOG_LEVEL", default_value = "info")]
    log_level: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    // Initialize logging
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&args.log_level));

    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(filter)
        .init();

    info!("Starting OpenCue Monitoring Indexer");

    // Load configuration
    let config = if let Some(config_path) = &args.config {
        Config::from_file(config_path)?
    } else {
        Config::from_args(&args)
    };

    info!(
        kafka_servers = %config.kafka.bootstrap_servers,
        group_id = %config.kafka.group_id,
        elasticsearch_url = %config.elasticsearch.url,
        "Configuration loaded"
    );

    // Initialize Elasticsearch client
    let es_client = ElasticsearchClient::new(&config.elasticsearch).await?;
    info!("Elasticsearch client initialized");

    // Create index templates
    es_client.create_index_templates().await?;
    info!("Index templates created/verified");

    // Start the consumer
    let consumer = EventConsumer::new(&config.kafka, es_client)?;
    info!("Kafka consumer initialized, starting event processing");

    // Run the consumer (blocks until shutdown)
    consumer.run().await?;

    info!("Indexer shutting down");
    Ok(())
}
