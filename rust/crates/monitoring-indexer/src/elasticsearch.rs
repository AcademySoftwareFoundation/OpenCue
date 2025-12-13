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

//! Elasticsearch client for indexing OpenCue monitoring events.

use chrono::Utc;
use elasticsearch::http::request::JsonBody;
use elasticsearch::http::transport::{SingleNodeConnectionPool, TransportBuilder};
use elasticsearch::indices::IndicesPutIndexTemplateParts;
use elasticsearch::{BulkParts, Elasticsearch};
use rayon::prelude::*;
use serde_json::json;
use tracing::{debug, error, info, warn};
use url::Url;

use crate::config::ElasticsearchConfig;
use crate::consumer::ConsumedEvent;
use crate::error::IndexerError;

/// Elasticsearch client wrapper for OpenCue event indexing
pub struct ElasticsearchClient {
    client: Elasticsearch,
    config: ElasticsearchConfig,
}

impl ElasticsearchClient {
    /// Create a new Elasticsearch client
    pub async fn new(config: &ElasticsearchConfig) -> Result<Self, IndexerError> {
        let url = Url::parse(&config.url)
            .map_err(|e| IndexerError::Elasticsearch(format!("Invalid URL: {}", e)))?;

        let pool = SingleNodeConnectionPool::new(url);
        let mut builder = TransportBuilder::new(pool);

        // Add authentication if provided
        if let (Some(username), Some(password)) = (&config.username, &config.password) {
            builder = builder.auth(elasticsearch::auth::Credentials::Basic(
                username.clone(),
                password.clone(),
            ));
        }

        let transport = builder
            .build()
            .map_err(|e| IndexerError::Elasticsearch(e.to_string()))?;

        let client = Elasticsearch::new(transport);

        // Verify connection
        let info = client
            .info()
            .send()
            .await
            .map_err(|e| IndexerError::Elasticsearch(format!("Connection failed: {}", e)))?;

        if !info.status_code().is_success() {
            return Err(IndexerError::Elasticsearch(
                "Failed to connect to Elasticsearch".to_string(),
            ));
        }

        info!(url = %config.url, "Connected to Elasticsearch");

        Ok(Self {
            client,
            config: config.clone(),
        })
    }

    /// Create index templates for all event types
    pub async fn create_index_templates(&self) -> Result<(), IndexerError> {
        let event_types = vec![
            ("job-events", self.job_events_mapping()),
            ("layer-events", self.layer_events_mapping()),
            ("frame-events", self.frame_events_mapping()),
            ("host-events", self.host_events_mapping()),
            ("proc-events", self.proc_events_mapping()),
        ];

        for (event_type, mappings) in event_types {
            self.create_index_template(event_type, mappings).await?;
        }

        Ok(())
    }

    /// Create a single index template
    async fn create_index_template(
        &self,
        event_type: &str,
        mappings: serde_json::Value,
    ) -> Result<(), IndexerError> {
        let template_name = format!("{}-{}", self.config.index_prefix, event_type);
        let index_pattern = format!("{}-{}-*", self.config.index_prefix, event_type);

        let body = json!({
            "index_patterns": [index_pattern],
            "template": {
                "settings": {
                    "number_of_shards": self.config.num_shards,
                    "number_of_replicas": self.config.num_replicas,
                    "index.mapping.total_fields.limit": 2000
                },
                "mappings": mappings
            },
            "priority": 100,
            "version": 1
        });

        let response = self
            .client
            .indices()
            .put_index_template(IndicesPutIndexTemplateParts::Name(&template_name))
            .body(body)
            .send()
            .await?;

        if response.status_code().is_success() {
            info!(template = %template_name, "Index template created/updated");
        } else {
            let error_body = response.text().await.unwrap_or_default();
            warn!(
                template = %template_name,
                error = %error_body,
                "Failed to create index template"
            );
        }

        Ok(())
    }

    /// Bulk index a batch of events
    pub async fn bulk_index(&self, events: &[ConsumedEvent]) -> Result<(), IndexerError> {
        if events.is_empty() {
            return Ok(());
        }

        let date_suffix = Utc::now().format("%Y.%m.%d").to_string();
        let index_prefix = &self.config.index_prefix;

        // Process events in parallel using rayon
        let results: Vec<_> = events
            .par_iter()
            .map(|event| {
                let index_name = format!(
                    "{}-{}-{}",
                    index_prefix,
                    event.event_type.index_suffix(),
                    date_suffix
                );

                // Index action
                let action: JsonBody<serde_json::Value>  = if let Some(ref event_id) = event.event_id {
                    json!({ "index": { "_index": index_name, "_id": event_id } })
                } else {
                    json!({ "index": { "_index": index_name } })
                }.into();

                // Document
                serde_json::from_str(&event.payload).map(|valid_doc| {
                    let document: JsonBody<serde_json::Value> = doc.into();
                    vec![action, doc]
                })
            })
            .collect();

        // Collect results and handle any errors
        let mut body: Vec<JsonBody<serde_json::Value>> = Vec::with_capacity(events.len() * 2);
        for result in results {
            body.extend(result?);
        }

        let response = self.client.bulk(BulkParts::None).body(body).send().await?;

        if response.status_code().is_success() {
            let response_body: serde_json::Value = response.json().await?;
            let errors = response_body
                .get("errors")
                .and_then(|e| e.as_bool())
                .unwrap_or(false);

            if errors {
                // Log individual errors
                if let Some(items) = response_body.get("items").and_then(|i| i.as_array()) {
                    for item in items {
                        if let Some(error) = item.get("index").and_then(|i| i.get("error")) {
                            warn!(error = %error, "Bulk index error for item");
                        }
                    }
                }
            } else {
                debug!(count = events.len(), "Bulk indexed events");
            }
        } else {
            let error_body = response.text().await.unwrap_or_default();
            error!(error = %error_body, "Bulk index request failed");
            return Err(IndexerError::Elasticsearch(error_body));
        }

        Ok(())
    }

    /// Common header mapping shared by all event types
    fn header_mapping() -> serde_json::Value {
        json!({
            "properties": {
                "event_id": { "type": "keyword" },
                "event_type": { "type": "keyword" },
                "timestamp": { "type": "date", "format": "epoch_millis" },
                "source_cuebot": { "type": "keyword" },
                "correlation_id": { "type": "keyword" }
            }
        })
    }

    /// Job events index mapping
    fn job_events_mapping(&self) -> serde_json::Value {
        json!({
            "properties": {
                "header": Self::header_mapping(),
                "job": {
                    "properties": {
                        "id": { "type": "keyword" },
                        "name": { "type": "keyword" },
                        "show": { "type": "keyword" },
                        "shot": { "type": "keyword" },
                        "user": { "type": "keyword" },
                        "state": { "type": "keyword" },
                        "facility": { "type": "keyword" },
                        "group": { "type": "keyword" },
                        "priority": { "type": "integer" },
                        "start_time": { "type": "date", "format": "epoch_millis" },
                        "stop_time": { "type": "date", "format": "epoch_millis" },
                        "is_paused": { "type": "boolean" },
                        "is_auto_eat": { "type": "boolean" },
                        "job_stats": {
                            "properties": {
                                "pending_frames": { "type": "integer" },
                                "running_frames": { "type": "integer" },
                                "dead_frames": { "type": "integer" },
                                "eaten_frames": { "type": "integer" },
                                "succeeded_frames": { "type": "integer" },
                                "waiting_frames": { "type": "integer" },
                                "depend_frames": { "type": "integer" },
                                "total_frames": { "type": "integer" },
                                "total_layers": { "type": "integer" },
                                "reserved_cores": { "type": "float" },
                                "reserved_gpus": { "type": "float" }
                            }
                        }
                    }
                },
                "previous_state": { "type": "keyword" },
                "reason": { "type": "text" },
                "killed_by": { "type": "keyword" }
            }
        })
    }

    /// Layer events index mapping
    fn layer_events_mapping(&self) -> serde_json::Value {
        json!({
            "properties": {
                "header": Self::header_mapping(),
                "layer": {
                    "properties": {
                        "id": { "type": "keyword" },
                        "name": { "type": "keyword" },
                        "type": { "type": "keyword" },
                        "range": { "type": "keyword" },
                        "chunk_size": { "type": "integer" },
                        "min_cores": { "type": "float" },
                        "max_cores": { "type": "float" },
                        "min_memory": { "type": "long" },
                        "min_gpus": { "type": "integer" },
                        "min_gpu_memory": { "type": "long" },
                        "is_threadable": { "type": "boolean" },
                        "tags": { "type": "keyword" },
                        "services": { "type": "keyword" },
                        "layer_stats": {
                            "properties": {
                                "pending_frames": { "type": "integer" },
                                "running_frames": { "type": "integer" },
                                "dead_frames": { "type": "integer" },
                                "eaten_frames": { "type": "integer" },
                                "succeeded_frames": { "type": "integer" },
                                "waiting_frames": { "type": "integer" },
                                "depend_frames": { "type": "integer" },
                                "total_frames": { "type": "integer" },
                                "reserved_cores": { "type": "float" },
                                "reserved_gpus": { "type": "float" },
                                "max_rss": { "type": "long" },
                                "total_core_seconds": { "type": "long" },
                                "total_gpu_seconds": { "type": "long" },
                                "rendered_frame_count": { "type": "integer" },
                                "failed_frame_count": { "type": "integer" },
                                "avg_frame_sec": { "type": "integer" },
                                "low_frame_sec": { "type": "integer" },
                                "high_frame_sec": { "type": "integer" }
                            }
                        }
                    }
                },
                "job_id": { "type": "keyword" },
                "job_name": { "type": "keyword" },
                "show": { "type": "keyword" }
            }
        })
    }

    /// Frame events index mapping
    fn frame_events_mapping(&self) -> serde_json::Value {
        json!({
            "properties": {
                "header": Self::header_mapping(),
                "frame": {
                    "properties": {
                        "id": { "type": "keyword" },
                        "name": { "type": "keyword" },
                        "number": { "type": "integer" },
                        "state": { "type": "keyword" },
                        "retry_count": { "type": "integer" },
                        "exit_status": { "type": "integer" },
                        "dispatch_order": { "type": "integer" },
                        "start_time": { "type": "date", "format": "epoch_millis" },
                        "stop_time": { "type": "date", "format": "epoch_millis" },
                        "max_rss": { "type": "long" },
                        "used_memory": { "type": "long" },
                        "reserved_memory": { "type": "long" },
                        "max_gpu_memory": { "type": "long" },
                        "used_gpu_memory": { "type": "long" },
                        "reserved_gpu_memory": { "type": "long" },
                        "last_resource": { "type": "keyword" },
                        "checkpoint_state": { "type": "keyword" },
                        "checkpoint_count": { "type": "integer" },
                        "total_core_time": { "type": "long" },
                        "total_gpu_time": { "type": "long" },
                        "llu_time": { "type": "date", "format": "epoch_millis" }
                    }
                },
                "layer_id": { "type": "keyword" },
                "job_id": { "type": "keyword" },
                "job_name": { "type": "keyword" },
                "show": { "type": "keyword" },
                "previous_state": { "type": "keyword" },
                "exit_signal": { "type": "integer" },
                "run_time": { "type": "integer" },
                "num_cores": { "type": "integer" },
                "num_gpus": { "type": "integer" },
                "host_name": { "type": "keyword" },
                "resource_id": { "type": "keyword" },
                "reason": { "type": "text" },
                "killed_by": { "type": "keyword" }
            }
        })
    }

    /// Host events index mapping
    fn host_events_mapping(&self) -> serde_json::Value {
        json!({
            "properties": {
                "header": Self::header_mapping(),
                "host": {
                    "properties": {
                        "id": { "type": "keyword" },
                        "name": { "type": "keyword" },
                        "state": { "type": "keyword" },
                        "lock_state": { "type": "keyword" },
                        "nimby_enabled": { "type": "boolean" },
                        "free_memory": { "type": "long" },
                        "total_memory": { "type": "long" },
                        "free_swap": { "type": "long" },
                        "total_swap": { "type": "long" },
                        "free_mcp": { "type": "long" },
                        "total_mcp": { "type": "long" },
                        "free_gpu_memory": { "type": "long" },
                        "total_gpu_memory": { "type": "long" },
                        "load": { "type": "integer" },
                        "cores": { "type": "float" },
                        "idle_cores": { "type": "float" },
                        "gpus": { "type": "integer" },
                        "idle_gpus": { "type": "integer" },
                        "procs": { "type": "integer" },
                        "boot_time": { "type": "date", "format": "epoch_millis" },
                        "ping_time": { "type": "date", "format": "epoch_millis" },
                        "tags": { "type": "keyword" },
                        "alloc_name": { "type": "keyword" },
                        "os": { "type": "keyword" }
                    }
                },
                "facility": { "type": "keyword" },
                "previous_state": { "type": "keyword" },
                "previous_lock_state": { "type": "keyword" },
                "nimby_locked": { "type": "boolean" },
                "reason": { "type": "text" }
            }
        })
    }

    /// Proc events index mapping
    fn proc_events_mapping(&self) -> serde_json::Value {
        json!({
            "properties": {
                "header": Self::header_mapping(),
                "proc_id": { "type": "keyword" },
                "proc_name": { "type": "keyword" },
                "host_id": { "type": "keyword" },
                "host_name": { "type": "keyword" },
                "job_id": { "type": "keyword" },
                "job_name": { "type": "keyword" },
                "layer_id": { "type": "keyword" },
                "layer_name": { "type": "keyword" },
                "frame_id": { "type": "keyword" },
                "frame_name": { "type": "keyword" },
                "show": { "type": "keyword" },
                "group_name": { "type": "keyword" },
                "reserved_cores": { "type": "float" },
                "reserved_gpus": { "type": "float" },
                "reserved_memory": { "type": "long" },
                "reserved_gpu_memory": { "type": "long" },
                "dispatch_time": { "type": "date", "format": "epoch_millis" },
                "booked_time": { "type": "date", "format": "epoch_millis" },
                "is_local_dispatch": { "type": "boolean" },
                "is_unbooked": { "type": "boolean" },
                "redirect_target": { "type": "keyword" },
                "services": { "type": "keyword" }
            }
        })
    }
}
