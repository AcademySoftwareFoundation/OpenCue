use std::sync::Arc;

use crate::{
    config::Config,
    consumer::{
        dispatcher::RqdDispatcher, frame_dao::FrameDao, host_dao::HostDao, layer_dao::LayerDao,
    },
    models::{DispatchJob, DispatchLayer, DispatchState, Host},
};
use futures::StreamExt;
use miette::Result;
use tracing::{error, info, warn};

pub struct JobMessageExecutor {
    host_dao: Arc<HostDao>,
    job_dao: LayerDao,
    dispatcher: RqdDispatcher,
}

impl JobMessageExecutor {
    pub async fn from_config(config: &Config) -> Result<Self> {
        let host_dao = Arc::new(HostDao::from_config(&config.database).await?);
        let layer_dao = LayerDao::from_config(&config.database).await?;
        let frame_dao = FrameDao::from_config(&config.database).await?;

        let dispatcher = RqdDispatcher::new(
            frame_dao,
            host_dao.clone(),
            config.rqd.grpc_port,
            config.queue.dispatch_frames_per_layer_limit,
            config.queue.core_multiplier,
            config.queue.memory_stranded_threshold.as_u64(),
        );
        Ok(JobMessageExecutor {
            host_dao,
            job_dao: layer_dao,
            dispatcher,
        })
    }

    pub async fn process(&self, job: DispatchJob) {
        let mut stream = self.job_dao.query_layers(job.id);
        // Stream elegible layers from this job and dispatch one by one
        while let Some(layer_model) = stream.next().await {
            let layer: Result<DispatchLayer, _> = layer_model.map(|l| l.into());
            match layer.map(|l| l.with_validation()) {
                Ok((dispatch_job, DispatchState::InvalidCoreMinRequirement)) => warn!(
                    "Consumed job {} with invalid Core Min requirement.",
                    dispatch_job.job_id
                ),
                Ok((dispatch_layer, DispatchState::Valid)) => {
                    let mut host_candidates_stream =
                        self.host_dao.find_host_for_job(&dispatch_layer);
                    // Attempt to dispatch host candidates and exist on the first successful attempt
                    while let Some(host_candidate) = host_candidates_stream.next().await {
                        match host_candidate {
                            Ok(host_model) => {
                                let host: Host = host_model.into();
                                info!(
                                    "Attempting host candidate {} for job {}",
                                    host.id, dispatch_layer.job_id
                                );
                                match self.dispatcher.dispatch(&dispatch_layer, &host).await {
                                    // Stop on the first successful attempt
                                    Ok(_) => break,
                                    Err(err) => warn!(
                                        "Failed to dispatch job {} on {}. {}",
                                        dispatch_layer.job_id, host.id, err
                                    ),
                                }
                            }
                            Err(err) => {
                                error!("Failed to consume Host stream. {err}");
                            }
                        }
                    }
                }
                Err(err) => {
                    error!(
                        "Consumed job {} but failed with unexpected db error. {}",
                        &job, err
                    );
                }
            }
        }
    }
}
