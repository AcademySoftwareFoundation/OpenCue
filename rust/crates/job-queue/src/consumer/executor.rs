use crate::{
    config::Config,
    consumer::{dispatcher::RqdDispatcher, host_fetcher::HostFetcher, layer_fetcher::LayerFetcher},
    models::{DispatchState, JobMessage},
};
use futures::StreamExt;
use miette::Result;
use tracing::{error, info, warn};

pub struct JobMessageExecutor {
    host_fetcher: HostFetcher,
    job_fetcher: LayerFetcher,
    dispatcher: RqdDispatcher,
}

impl JobMessageExecutor {
    pub async fn from_config(config: &Config) -> Result<Self> {
        let host_fetcher = HostFetcher::from_config(&config.database).await?;
        let layer_fetcher = LayerFetcher::from_config(&config.database).await?;
        let dispatcher = RqdDispatcher {
            grpc_port: config.rqd.grpc_port,
        };
        Ok(JobMessageExecutor {
            host_fetcher,
            job_fetcher: layer_fetcher,
            dispatcher,
        })
    }

    pub async fn process(&self, job_message: JobMessage) {
        let mut stream = self.job_fetcher.query_job(job_message.pk_job.clone());
        // Stream elegible layers from this job and dispatch one by one
        while let Some(layer) = stream.next().await {
            match layer.map(|l| l.with_validation()) {
                Ok((dispatch_job, DispatchState::InvalidCoreMinRequirement)) => warn!(
                    "Consumed job {} with invalid Core Min requirement.",
                    dispatch_job.pk_job
                ),
                Ok((dispatch_layer, DispatchState::Valid)) => {
                    let mut host_candidates_stream =
                        self.host_fetcher.find_host_for_job(&dispatch_layer);
                    // Attempt to dispatch host candidates and exist on the first successful attempt
                    while let Some(host_candidate) = host_candidates_stream.next().await {
                        match host_candidate {
                            Ok(host) => {
                                info!(
                                    "Attempting host candidate {} for job {}",
                                    host.pk_host, dispatch_layer.pk_job
                                );
                                match self.dispatcher.dispatch(&host, &dispatch_layer).await {
                                    Ok(_) => break,
                                    Err(err) => warn!(
                                        "Failed to dispatch job {} on {}. {}",
                                        dispatch_layer.pk_job, host.pk_host, err
                                    ),
                                }
                            }
                            Err(_) => todo!(),
                        }
                    }
                }
                Err(err) => match err {
                    sqlx::Error::RowNotFound => warn!(
                        "Consumed job {} which couldn't be found on the database.",
                        &job_message.pk_job
                    ),
                    _ => error!(
                        "Consumed job {} but failed with unexpected db error. {}",
                        &job_message, err
                    ),
                },
            }
        }
    }
}
