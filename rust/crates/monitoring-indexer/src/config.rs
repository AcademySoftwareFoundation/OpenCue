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

//! Configuration for the OpenCue monitoring indexer.

use serde::Deserialize;

use crate::error::IndexerError;

/// Kafka topic for job events
pub const TOPIC_JOB_EVENTS: &str = "opencue.job.events";
/// Kafka topic for layer events
pub const TOPIC_LAYER_EVENTS: &str = "opencue.layer.events";
/// Kafka topic for frame events
pub const TOPIC_FRAME_EVENTS: &str = "opencue.frame.events";
/// Kafka topic for host events
pub const TOPIC_HOST_EVENTS: &str = "opencue.host.events";
/// Kafka topic for proc events
pub const TOPIC_PROC_EVENTS: &str = "opencue.proc.events";

/// Top-level configuration
#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub kafka: KafkaConfig,
    pub elasticsearch: ElasticsearchConfig,
}

/// Kafka consumer configuration
#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
pub struct KafkaConfig {
    /// Kafka bootstrap servers (comma-separated)
    pub bootstrap_servers: String,
    /// Consumer group ID
    pub group_id: String,
    /// Auto offset reset policy
    pub auto_offset_reset: String,
    /// Enable auto commit
    pub enable_auto_commit: bool,
    /// Auto commit interval in milliseconds
    pub auto_commit_interval_ms: u32,
    /// Maximum poll records
    pub max_poll_records: u32,
    /// Session timeout in milliseconds
    pub session_timeout_ms: u32,
    /// Topics to subscribe to
    pub topics: Vec<String>,
}

/// Elasticsearch client configuration
#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
pub struct ElasticsearchConfig {
    /// Elasticsearch URL
    pub url: String,
    /// Username for authentication (optional)
    pub username: Option<String>,
    /// Password for authentication (optional)
    pub password: Option<String>,
    /// Index prefix
    pub index_prefix: String,
    /// Number of shards for indices
    pub num_shards: u32,
    /// Number of replicas for indices
    pub num_replicas: u32,
    /// Bulk indexing batch size
    pub bulk_size: usize,
    /// Bulk indexing flush interval in milliseconds
    pub flush_interval_ms: u64,
}

impl Config {
    /// Load configuration from a file
    pub fn from_file(path: &str) -> Result<Self, IndexerError> {
        let settings = config::Config::builder()
            .add_source(config::File::with_name(path))
            .add_source(config::Environment::with_prefix("INDEXER").separator("_"))
            .build()
            .map_err(|e| IndexerError::Config(e.to_string()))?;

        settings
            .try_deserialize()
            .map_err(|e| IndexerError::Config(e.to_string()))
    }

    /// Create configuration from CLI arguments
    pub fn from_args(args: &super::Args) -> Self {
        Config {
            kafka: KafkaConfig {
                bootstrap_servers: args.kafka_servers.clone(),
                group_id: args.kafka_group_id.clone(),
                ..Default::default()
            },
            elasticsearch: ElasticsearchConfig {
                url: args.elasticsearch_url.clone(),
                username: args.elasticsearch_username.clone(),
                password: args.elasticsearch_password.clone(),
                index_prefix: args.index_prefix.clone(),
                ..Default::default()
            },
        }
    }
}

impl Default for KafkaConfig {
    fn default() -> Self {
        Self {
            bootstrap_servers: "localhost:9092".to_string(),
            group_id: "opencue-monitoring-indexer".to_string(),
            auto_offset_reset: "earliest".to_string(),
            enable_auto_commit: true,
            auto_commit_interval_ms: 5000,
            max_poll_records: 500,
            session_timeout_ms: 30000,
            topics: vec![
                TOPIC_JOB_EVENTS.to_string(),
                TOPIC_LAYER_EVENTS.to_string(),
                TOPIC_FRAME_EVENTS.to_string(),
                TOPIC_HOST_EVENTS.to_string(),
                TOPIC_PROC_EVENTS.to_string(),
            ],
        }
    }
}

impl Default for ElasticsearchConfig {
    fn default() -> Self {
        Self {
            url: "http://localhost:9200".to_string(),
            username: None,
            password: None,
            index_prefix: "opencue".to_string(),
            num_shards: 1,
            num_replicas: 0,
            bulk_size: 100,
            flush_interval_ms: 5000,
        }
    }
}
