use crate::{
    config::CONFIG, job_dispatcher::event_handler::BookJobEventHandler, models::DispatchJob,
};
use futures::StreamExt;
use miette::{Context, IntoDiagnostic, Result};
use moka::future::Cache;
use rdkafka::{
    ClientConfig, Message,
    consumer::{Consumer, StreamConsumer},
};
use tracing::{error, info, warn};
use uuid::Uuid;

/// General job dispatcher that coordinates Kafka message consumption with job processing.
/// 
/// This is the main entry point for the job dispatch system, wrapping a Kafka consumer
/// that processes dispatch job messages from the queue.
pub struct GeneralJobDispatcher {
    consumer: KafkaJobConsumer,
}

impl GeneralJobDispatcher {
    /// Creates a new general job dispatcher with Kafka consumer and event handler.
    /// 
    /// Sets up the complete dispatch pipeline including database connections,
    /// Kafka consumer configuration, and job event handling.
    /// 
    /// # Returns
    /// * `Ok(GeneralJobDispatcher)` - Configured dispatcher ready to process jobs
    /// * `Err(miette::Error)` - If initialization fails (typically database connection issues)
    pub async fn new() -> Result<Self> {
        let job_dispatcher = BookJobEventHandler::new()
            .await
            .wrap_err("Failed to start JobMessageExecutor, possibly a database connection error")?;

        let consumer = KafkaJobConsumer::new(
            &CONFIG.kafka.bootstrap_servers,
            CONFIG.kafka.general_jobs_topic.topic_name.clone(),
            job_dispatcher,
        )?;

        Ok(GeneralJobDispatcher { consumer })
    }
}

/// Kafka consumer for processing job dispatch messages.
/// 
/// Handles:
/// - Kafka message consumption and deserialization
/// - Job back-off caching to prevent repeated processing
/// - Message acknowledgment and error handling
/// - Integration with job event handler for dispatch processing
pub struct KafkaJobConsumer {
    id: Uuid,
    topic_name: String,
    consumer: StreamConsumer,
    event_handler: BookJobEventHandler,
    back_off_cache: Cache<Uuid, ()>,
}

impl KafkaJobConsumer {
    /// Creates a new Kafka job consumer with the specified configuration.
    /// 
    /// Configures the Kafka consumer with:
    /// - Bootstrap servers for cluster connection
    /// - Consumer group membership for load balancing
    /// - Manual commit mode for reliable message processing
    /// - Back-off cache to prevent duplicate job processing
    /// 
    /// # Arguments
    /// * `bootstrap_servers` - Comma-separated list of Kafka broker addresses
    /// * `topic_name` - Name of the Kafka topic to consume from
    /// * `dispatcher` - Event handler for processing consumed jobs
    /// 
    /// # Returns
    /// * `Ok(KafkaJobConsumer)` - Configured consumer ready to start processing
    /// * `Err(miette::Error)` - If Kafka client creation fails
    pub fn new(
        bootstrap_servers: &str,
        topic_name: String,
        dispatcher: BookJobEventHandler,
    ) -> Result<Self> {
        let id = Uuid::new_v4();
        let consumer = ClientConfig::new()
            .set("bootstrap.servers", bootstrap_servers)
            .set("group.id", "opencue-job-dispatchers")
            .set("client.id", id)
            .set("enable.auto.commit", "false") // Manual commit for better control
            .set("auto.offset.reset", "earliest")
            .set("max.poll.interval.ms", "300000") // 5 minutes
            .set("session.timeout.ms", "30000")
            .set("heartbeat.interval.ms", "3000")
            .create()
            .into_diagnostic()
            .wrap_err("Failed to start Kafka consumer client")?;

        let back_off_cache = Cache::builder()
            .time_to_live(CONFIG.queue.job_back_off_duration)
            .build();

        Ok(KafkaJobConsumer {
            id,
            topic_name,
            consumer,
            event_handler: dispatcher,
            back_off_cache,
        })
    }

    /// Starts the Kafka consumer to process job dispatch messages.
    /// 
    /// This is the main processing loop that:
    /// 1. Subscribes to the configured Kafka topic
    /// 2. Continuously consumes messages from the stream
    /// 3. Deserializes job messages and processes them via the event handler
    /// 4. Implements back-off caching to prevent duplicate processing
    /// 5. Commits messages after successful processing
    /// 
    /// The loop runs indefinitely until an unrecoverable error occurs.
    /// 
    /// # Returns
    /// * `Ok(())` - Should never return normally (runs indefinitely)
    /// * `Err(miette::Error)` - If subscription fails or other critical errors occur
    pub async fn start(&self) -> Result<()> {
        self.consumer
            .subscribe(&[&self.topic_name])
            .into_diagnostic()
            .wrap_err("Failed to subscribe to topic")?;

        info!(
            "Job Dispatcher {} started consuming {}",
            self.id, self.topic_name
        );

        let mut message_stream = self.consumer.stream();
        while let Some(message) = message_stream.next().await {
            info!("Got message");
            match message {
                Ok(msg) => {
                    if let Some(payload) = msg.payload() {
                        let serialized_job = String::from_utf8_lossy(payload);
                        match serde_json::from_str::<DispatchJob>(&serialized_job) {
                            Ok(job) => {
                                if self.back_off_cache.contains_key(&job.id) {
                                    info!("Skipping job {}", job);
                                } else {
                                    info!("Consumed job {}", job);
                                    self.back_off_cache.insert(job.id, ()).await;
                                    self.event_handler.process(job).await;
                                }
                            }
                            Err(err) => {
                                warn!("Failed to deserialize job: {}", err);
                                // TODO: push failed message to a different queue
                            }
                        }
                    }

                    if let Err(err) = self
                        .consumer
                        .commit_message(&msg, rdkafka::consumer::CommitMode::Async)
                    {
                        warn!("Failed to commit message. {}", err);
                    }
                }
                Err(err) => {
                    error!("Error receiving kafka message: {}", err);
                }
            }
        }
        Ok(())
    }
}

impl std::ops::Deref for GeneralJobDispatcher {
    type Target = KafkaJobConsumer;

    fn deref(&self) -> &Self::Target {
        &self.consumer
    }
}
