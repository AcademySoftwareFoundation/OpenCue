use std::{marker::PhantomData, time::Duration};

use miette::{Context, IntoDiagnostic, Result};
use rdkafka::{
    ClientConfig,
    admin::{AdminClient, AdminOptions, NewTopic, TopicReplication},
    client::DefaultClientContext,
    producer::{FutureProducer, FutureRecord},
    types::RDKafkaErrorCode,
    util::Timeout,
};
use serde::Serialize;
use tracing::{error, info, trace};

use crate::{
    config::{KafkaConfig, TopicConfig},
    models::{JobMessage, Partitionable},
};

pub struct GeneralJobQueue {
    producer: KafkaTopicProducer<JobMessage>,
}

impl GeneralJobQueue {
    pub fn from_config(config: &KafkaConfig) -> Result<Self> {
        let producer: KafkaTopicProducer<JobMessage> =
            KafkaTopicProducer::new(config, &config.general_jobs_topic)?;

        Ok(Self { producer })
    }
}

pub struct KafkaTopicProducer<T> {
    topic_name: String,
    num_partitions: i32,
    replication_factor: i32,
    retention: Duration,
    producer: FutureProducer,
    config: KafkaConfig,
    _phantom: PhantomData<T>,
}

impl<T: Serialize + Partitionable> KafkaTopicProducer<T> {
    pub fn new(config: &KafkaConfig, topic_config: &TopicConfig) -> Result<Self> {
        let producer: FutureProducer = ClientConfig::new()
            .set("bootstrap.servers", &config.bootstrap_servers)
            .create()
            .into_diagnostic()?;

        Ok(KafkaTopicProducer {
            topic_name: topic_config.topic_name.clone(),
            num_partitions: topic_config.num_partitions,
            replication_factor: topic_config.replication_factor,
            retention: topic_config.retention,
            producer,
            config: config.clone(),
            _phantom: PhantomData,
        })
    }

    pub async fn send(&self, payload: &T) -> Result<()> {
        let serialized_payload = serde_json::to_string(payload)
            .into_diagnostic()
            .wrap_err("Failed to serialize payload")?;
        let key = payload.partition_key();
        let record = FutureRecord::to(&self.topic_name)
            .payload(&serialized_payload)
            .key(key);

        match self
            .producer
            .send(record, Timeout::After(self.config.timeout))
            .await
        {
            Ok(delivery) => {
                trace!(
                    "Message sent with key {} to {} at partition {}",
                    key, self.topic_name, delivery.partition
                );
            }
            Err((kafka_error, _)) => {
                error!(
                    "Failed to deliver message with key {} to {}. {}",
                    key, self.topic_name, kafka_error
                )
            }
        }
        Ok(())
    }

    pub async fn create_topic(&self) -> Result<()> {
        let admin_client: AdminClient<DefaultClientContext> = ClientConfig::new()
            .set("bootstrap.servers", &self.config.bootstrap_servers)
            .create()
            .into_diagnostic()
            .wrap_err("Failed to connect AdminClient")?;

        let retention = self.retention.as_millis().to_string();

        info!("Replication = {}", self.replication_factor);
        let new_topic = NewTopic::new(
            &self.topic_name,
            self.num_partitions,
            TopicReplication::Fixed(self.replication_factor),
        )
        // How long messages are retained in the topic before being deleted
        .set("retention.ms", &retention)
        // Use log compaction to keep only the latest value for each key
        .set("cleanup.policy", "compact")
        // Minimum ratio of dirty (uncompacted) records to total records before compaction triggers
        .set("min.cleanable.dirty.ratio", "0.1")
        // Maximum time a segment is kept open before being closed and made available for compaction
        .set("segment.ms", "60000") // 1 min
        // How long to retain delete tombstone markers for compacted topics
        .set("delete.retention.ms", "60000") // 1 minute
        // Maximum size of a single log segment file before rolling to a new segment
        .set("segment.bytes", "5242880"); // 5MB
        let options = AdminOptions::new().operation_timeout(Some(Duration::from_secs(30)));

        let results = admin_client
            .create_topics(&[new_topic], &options)
            .await
            .into_diagnostic()
            .wrap_err("Failed to create topic")?;

        for result in results {
            match result {
                Ok(topic) => info!("Topic '{}' created successfully", topic),
                Err((topic, RDKafkaErrorCode::TopicAlreadyExists)) => {
                    info!("Topic '{}' already exists.", topic)
                }
                Err((_topic, error)) => Err(error)
                    .into_diagnostic()
                    .wrap_err("Failed to create topic")?,
            }
        }
        Ok(())
    }
}

impl std::ops::Deref for GeneralJobQueue {
    type Target = KafkaTopicProducer<JobMessage>;

    fn deref(&self) -> &Self::Target {
        &self.producer
    }
}
