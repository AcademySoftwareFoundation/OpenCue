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

//! Kafka consumer for OpenCue monitoring events.

use std::sync::Arc;
use std::time::Duration;

use rdkafka::config::ClientConfig;
use rdkafka::consumer::{CommitMode, Consumer, StreamConsumer};
use rdkafka::error::KafkaError;
use rdkafka::message::Message;
use rdkafka::types::RDKafkaErrorCode;
use tokio::sync::mpsc;
use tracing::{debug, error, info, warn};

use crate::config::{
    KafkaConfig, TOPIC_FRAME_EVENTS, TOPIC_HOST_EVENTS, TOPIC_JOB_EVENTS, TOPIC_LAYER_EVENTS,
    TOPIC_PROC_EVENTS,
};
use crate::elasticsearch::ElasticsearchClient;
use crate::error::IndexerError;

/// Event types for routing to appropriate indices
#[derive(Debug, Clone)]
pub enum EventType {
    Job,
    Layer,
    Frame,
    Host,
    Proc,
}

impl EventType {
    /// Determine event type from Kafka topic name
    pub fn from_topic(topic: &str) -> Option<Self> {
        match topic {
            TOPIC_JOB_EVENTS => Some(EventType::Job),
            TOPIC_LAYER_EVENTS => Some(EventType::Layer),
            TOPIC_FRAME_EVENTS => Some(EventType::Frame),
            TOPIC_HOST_EVENTS => Some(EventType::Host),
            TOPIC_PROC_EVENTS => Some(EventType::Proc),
            _ => None,
        }
    }

    /// Get the index suffix for this event type
    pub fn index_suffix(&self) -> &'static str {
        match self {
            EventType::Job => "job-events",
            EventType::Layer => "layer-events",
            EventType::Frame => "frame-events",
            EventType::Host => "host-events",
            EventType::Proc => "proc-events",
        }
    }
}

/// A consumed event ready for indexing
#[derive(Debug)]
pub struct ConsumedEvent {
    pub event_type: EventType,
    pub event_id: Option<String>,
    pub payload: String,
}

/// Kafka consumer for OpenCue monitoring events
pub struct EventConsumer {
    consumer: StreamConsumer,
    es_client: Arc<ElasticsearchClient>,
}

impl EventConsumer {
    /// Create a new event consumer
    pub fn new(config: &KafkaConfig, es_client: ElasticsearchClient) -> Result<Self, IndexerError> {
        let consumer: StreamConsumer = ClientConfig::new()
            .set("bootstrap.servers", &config.bootstrap_servers)
            .set("group.id", &config.group_id)
            .set("auto.offset.reset", &config.auto_offset_reset)
            .set("enable.auto.commit", config.enable_auto_commit.to_string())
            .set(
                "auto.commit.interval.ms",
                config.auto_commit_interval_ms.to_string(),
            )
            .set("session.timeout.ms", config.session_timeout_ms.to_string())
            .set("enable.partition.eof", "false")
            .create()?;

        // Subscribe to all topics
        let topics: Vec<&str> = config.topics.iter().map(|s| s.as_str()).collect();
        consumer.subscribe(&topics)?;

        info!(topics = ?topics, "Subscribed to Kafka topics");

        Ok(Self {
            consumer,
            es_client: Arc::new(es_client),
        })
    }

    /// Run the consumer loop
    pub async fn run(self) -> Result<(), IndexerError> {
        let (tx, rx) = mpsc::channel::<ConsumedEvent>(1000);
        let es_client = self.es_client.clone();

        // Spawn indexer task
        let indexer_handle = tokio::spawn(run_indexer_loop(rx, es_client));

        // Run consumer loop
        self.consume_messages(tx).await;

        // Wait for indexer to finish
        indexer_handle.await.ok();

        Ok(())
    }

    /// Consume messages from Kafka and send them to the indexer
    async fn consume_messages(&self, tx: mpsc::Sender<ConsumedEvent>) {
        loop {
            match self.consumer.recv().await {
                Ok(message) => {
                    let topic = message.topic();
                    let partition = message.partition();
                    let offset = message.offset();

                    if let Some(payload) = message.payload() {
                        let payload_str = match std::str::from_utf8(payload) {
                            Ok(s) => s.to_string(),
                            Err(e) => {
                                warn!(
                                    topic = topic,
                                    partition = partition,
                                    offset = offset,
                                    error = %e,
                                    "Invalid UTF-8 in message payload"
                                );
                                continue;
                            }
                        };

                        if let Some(event_type) = EventType::from_topic(topic) {
                            // Extract event_id from JSON
                            let event_id = extract_event_id(&payload_str);

                            debug!(
                                topic = topic,
                                partition = partition,
                                offset = offset,
                                event_id = ?event_id,
                                "Received event"
                            );

                            let event = ConsumedEvent {
                                event_type,
                                event_id,
                                payload: payload_str,
                            };

                            if tx.send(event).await.is_err() {
                                error!("Indexer task has stopped, shutting down consumer");
                                break;
                            }
                        } else {
                            warn!(topic = topic, "Unknown topic, skipping message");
                        }
                    }

                    // Commit offset
                    if let Err(e) = self.consumer.commit_message(&message, CommitMode::Async) {
                        warn!(error = %e, "Failed to commit offset");
                    }
                }
                Err(e) => {
                    // Check if this is an expected "topic not found" error during startup
                    if is_topic_not_found_error(&e) {
                        debug!(error = %e, "Waiting for Kafka topics to be created");
                        tokio::time::sleep(Duration::from_secs(5)).await;
                    } else {
                        error!(error = %e, "Error receiving message from Kafka");
                        tokio::time::sleep(Duration::from_millis(100)).await;
                    }
                }
            }
        }
    }
}

/// Run the indexer loop that batches events and sends them to Elasticsearch
async fn run_indexer_loop(
    mut rx: mpsc::Receiver<ConsumedEvent>,
    es_client: Arc<ElasticsearchClient>,
) {
    let mut batch: Vec<ConsumedEvent> = Vec::with_capacity(100);
    let mut interval = tokio::time::interval(Duration::from_secs(5));

    loop {
        tokio::select! {
            event = rx.recv() => {
                match event {
                    Some(e) => {
                        batch.push(e);
                        if batch.len() >= 100 {
                            match es_client.bulk_index(&batch).await {
                                Ok(_) => {
                                    batch.clear();
                                    interval.reset();
                                }
                                Err(e) => {
                                    error!(error = %e, "Failed to bulk index events");
                                }
                            }
                        }
                    }
                    None => {
                        // Channel closed, flush remaining
                        if !batch.is_empty() {
                            if let Err(e) = es_client.bulk_index(&batch).await {
                                error!(error = %e, "Failed to flush remaining events");
                            }
                        }
                        break;
                    }
                }
            }
            _ = interval.tick() => {
                if !batch.is_empty() {
                    match es_client.bulk_index(&batch).await {
                        Ok(_) => {
                            batch.clear();
                        }
                        Err(e) => {
                            error!(error = %e, "Failed to flush events on interval");
                        }
                    }
                }
            }
        }
    }
}

/// Check if a Kafka error is due to topic not existing yet
fn is_topic_not_found_error(e: &KafkaError) -> bool {
    match e {
        KafkaError::MessageConsumption(code) => {
            matches!(code, RDKafkaErrorCode::UnknownTopicOrPartition)
        }
        _ => false,
    }
}

/// Extract event_id from JSON payload
fn extract_event_id(json: &str) -> Option<String> {
    serde_json::from_str::<serde_json::Value>(json)
        .ok()
        .and_then(|v| {
            v.get("header")
                .and_then(|h| h.get("event_id"))
                .and_then(|id| id.as_str())
                .map(|s| s.to_string())
        })
}
