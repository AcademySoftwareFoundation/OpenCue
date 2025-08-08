use crate::{config::Config, consumer::executor::JobMessageExecutor, models::DispatchJob};
use futures::StreamExt;
use miette::{Context, IntoDiagnostic, Result};
use rdkafka::{
    ClientConfig, Message,
    consumer::{Consumer, StreamConsumer},
};
use tracing::{error, info, warn};
use uuid::Uuid;

pub struct GeneralJobDispatcher {
    consumer: KafkaJobConsumer,
}

impl GeneralJobDispatcher {
    pub async fn from_config(config: &Config) -> Result<Self> {
        let job_dispatcher = JobMessageExecutor::from_config(config)
            .await
            .wrap_err("Failed to start JobMessageExecutor, possibly a database connection error")?;

        let consumer = KafkaJobConsumer::new(
            &config.kafka.bootstrap_servers,
            config.kafka.general_jobs_topic.topic_name.clone(),
            job_dispatcher,
        )?;

        Ok(GeneralJobDispatcher { consumer })
    }
}

pub struct KafkaJobConsumer {
    id: Uuid,
    topic_name: String,
    consumer: StreamConsumer,
    dispatcher: JobMessageExecutor,
}

impl KafkaJobConsumer {
    pub fn new(
        bootstrap_servers: &str,
        topic_name: String,
        dispatcher: JobMessageExecutor,
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

        Ok(KafkaJobConsumer {
            id,
            topic_name,
            consumer,
            dispatcher,
        })
    }

    pub async fn start(&self, dry_run: bool) -> Result<()> {
        self.consumer
            .subscribe(&[&self.topic_name])
            .into_diagnostic()
            .wrap_err("Failed to subsctibe to topic")?;

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
                                if dry_run {
                                    info!("(dry-run) Consumed job {}", job);
                                } else {
                                    self.dispatcher.process(job).await;
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
