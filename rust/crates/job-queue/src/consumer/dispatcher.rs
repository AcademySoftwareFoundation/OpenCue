use crate::{
    config::RqdConfig,
    models::{DispatchLayer, HostModel},
};
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::rqd::{
    RqdStaticLaunchFrameRequest, RunFrame, rqd_interface_client::RqdInterfaceClient,
};
use tonic::transport::Channel;
use uuid::Uuid;

pub struct RqdDispatcher {
    pub grpc_port: u32,
}

impl RqdDispatcher {
    pub async fn dispatch(&self, host: &HostModel, dispatch_job: &DispatchLayer) -> Result<()> {
        // Lock host on database?
        let mut rqd_client = Self::connect_to_rqd(&host.str_name, self.grpc_port).await?;

        // let run_frame = RunFrame {
        //     resource_id: ,
        //     job_id:,
        //     job_name:,
        //     frame_id:,
        //     frame_name:,
        //     layer_id:,
        //     command:,
        //     user_name:,
        //     log_dir:,
        //     show:,
        //     shot:,
        //     frame_temp_dir:,
        //     num_cores:,
        //     gid:,
        //     ignore_nimby:,
        //     environment:,
        //     attributes:,
        //     num_gpus:,
        //     children: None,
        //     uid_optional: uid.map(|uid| UidOptional::Uid(uid as i32)),
        //     os:,
        //     soft_memory_limit: 0,
        //     hard_memory_limit: 0,
        //     pid: 0,
        //     loki_url: "".to_string(),

        //     #[allow(deprecated)]
        //     job_temp_dir: "deprecated".to_string(),

        //     #[allow(deprecated)]
        //     log_file: "deprecated".to_string(),

        //     #[allow(deprecated)]
        //     log_dir_file: "deprecated".to_string(),

        //     #[allow(deprecated)]
        //     start_time: 0,
        // };

        // let request = RqdStaticLaunchFrameRequest {
        //     run_frame: Some(run_frame),
        // };
        // rqd_client
        //     .launch_frame(request)
        //     .await
        //     .into_diagnostic()
        //     .and(Ok(()))
        Ok(())
    }

    async fn connect_to_rqd(hostname: &str, port: u32) -> Result<RqdInterfaceClient<Channel>> {
        let client = RqdInterfaceClient::connect(format!("http://{}:{}", hostname, port))
            .await
            .into_diagnostic()
            .wrap_err(format!(
                "Failed to connect to Rqd Server: {}:{}",
                hostname, port
            ))?;
        Ok(client)
    }
}
