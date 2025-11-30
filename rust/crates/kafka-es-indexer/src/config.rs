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

//! Configuration for the Kafka-Elasticsearch indexer.

use serde::Deserialize;

use crate::error::IndexerError;

/// Top-level configuration
#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub kafka: KafkaConfig,
    pub elasticsearch: ElasticsearchConfig,
}

/// Kafka consumer configuration
#[derive(Debug, Clone, Deserialize)]
pub struct KafkaConfig {
    /// Kafka bootstrap servers (comma-separated)
    #[serde(default = "default_bootstrap_servers")]
    pub bootstrap_servers: String,

    /// Consumer group ID
    #[serde(default = "default_group_id")]
    pub group_id: String,

    /// Auto offset reset policy
    #[serde(default = "default_auto_offset_reset")]
    pub auto_offset_reset: String,

    /// Enable auto commit
    #[serde(default = "default_enable_auto_commit")]
    pub enable_auto_commit: bool,

    /// Auto commit interval in milliseconds
    #[serde(default = "default_auto_commit_interval")]
    pub auto_commit_interval_ms: u32,

    /// Maximum poll records
    #[serde(default = "default_max_poll_records")]
    pub max_poll_records: u32,

    /// Session timeout in milliseconds
    #[serde(default = "default_session_timeout")]
    pub session_timeout_ms: u32,

    /// Topics to subscribe to
    #[serde(default = "default_topics")]
    pub topics: Vec<String>,
}

/// Elasticsearch client configuration
#[derive(Debug, Clone, Deserialize)]
pub struct ElasticsearchConfig {
    /// Elasticsearch URL
    #[serde(default = "default_elasticsearch_url")]
    pub url: String,

    /// Username for authentication (optional)
    pub username: Option<String>,

    /// Password for authentication (optional)
    pub password: Option<String>,

    /// Index prefix
    #[serde(default = "default_index_prefix")]
    pub index_prefix: String,

    /// Number of shards for indices
    #[serde(default = "default_num_shards")]
    pub num_shards: u32,

    /// Number of replicas for indices
    #[serde(default = "default_num_replicas")]
    pub num_replicas: u32,

    /// Bulk indexing batch size
    #[serde(default = "default_bulk_size")]
    pub bulk_size: usize,

    /// Bulk indexing flush interval in milliseconds
    #[serde(default = "default_flush_interval")]
    pub flush_interval_ms: u64,
}

// Default value functions
fn default_bootstrap_servers() -> String {
    "localhost:9092".to_string()
}

fn default_group_id() -> String {
    "opencue-elasticsearch-indexer".to_string()
}

fn default_auto_offset_reset() -> String {
    "earliest".to_string()
}

fn default_enable_auto_commit() -> bool {
    true
}

fn default_auto_commit_interval() -> u32 {
    5000
}

fn default_max_poll_records() -> u32 {
    500
}

fn default_session_timeout() -> u32 {
    30000
}

fn default_topics() -> Vec<String> {
    vec![
        "opencue.job.events".to_string(),
        "opencue.layer.events".to_string(),
        "opencue.frame.events".to_string(),
        "opencue.host.events".to_string(),
        "opencue.proc.events".to_string(),
    ]
}

fn default_elasticsearch_url() -> String {
    "http://localhost:9200".to_string()
}

fn default_index_prefix() -> String {
    "opencue".to_string()
}

fn default_num_shards() -> u32 {
    1
}

fn default_num_replicas() -> u32 {
    0
}

fn default_bulk_size() -> usize {
    100
}

fn default_flush_interval() -> u64 {
    5000
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
                auto_offset_reset: default_auto_offset_reset(),
                enable_auto_commit: default_enable_auto_commit(),
                auto_commit_interval_ms: default_auto_commit_interval(),
                max_poll_records: default_max_poll_records(),
                session_timeout_ms: default_session_timeout(),
                topics: default_topics(),
            },
            elasticsearch: ElasticsearchConfig {
                url: args.elasticsearch_url.clone(),
                username: None,
                password: None,
                index_prefix: args.index_prefix.clone(),
                num_shards: default_num_shards(),
                num_replicas: default_num_replicas(),
                bulk_size: default_bulk_size(),
                flush_interval_ms: default_flush_interval(),
            },
        }
    }
}

impl Default for KafkaConfig {
    fn default() -> Self {
        Self {
            bootstrap_servers: default_bootstrap_servers(),
            group_id: default_group_id(),
            auto_offset_reset: default_auto_offset_reset(),
            enable_auto_commit: default_enable_auto_commit(),
            auto_commit_interval_ms: default_auto_commit_interval(),
            max_poll_records: default_max_poll_records(),
            session_timeout_ms: default_session_timeout(),
            topics: default_topics(),
        }
    }
}

impl Default for ElasticsearchConfig {
    fn default() -> Self {
        Self {
            url: default_elasticsearch_url(),
            username: None,
            password: None,
            index_prefix: default_index_prefix(),
            num_shards: default_num_shards(),
            num_replicas: default_num_replicas(),
            bulk_size: default_bulk_size(),
            flush_interval_ms: default_flush_interval(),
        }
    }
}
