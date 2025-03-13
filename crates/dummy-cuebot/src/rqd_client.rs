use std::{collections::HashMap, sync::Arc};

use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::rqd::{
    self as pb, RunFrame, rqd_interface_client::RqdInterfaceClient, run_frame::UidOptional,
};
use tokio::sync::Mutex;
use tonic::transport::Channel;
use uuid::Uuid;

pub struct DummyRqdClient {
    client: Arc<Mutex<RqdInterfaceClient<Channel>>>,
}

impl DummyRqdClient {
    pub async fn build(hostname: String, port: u16) -> Result<Self> {
        let client = RqdInterfaceClient::connect(format!("http://{}:{}", hostname, port))
            .await
            .into_diagnostic()
            .wrap_err(format!(
                "Failed to connect to Rqd Server: {}:{}",
                hostname, port
            ))?;
        Ok(Self {
            client: Arc::new(Mutex::new(client)),
        })
    }

    pub async fn launch_frame(
        &self,
        cmd: String,
        env_vars: HashMap<String, String>,
        uid: Option<u32>,
    ) -> Result<()> {
        let run_frame = RunFrame {
            resource_id: Uuid::new_v4().to_string(),
            job_id: Uuid::new_v4().to_string(),
            job_name: "test_job".to_string(),
            frame_id: Uuid::new_v4().to_string(),
            frame_name: "test_frame".to_string(),
            layer_id: Uuid::new_v4().to_string(),
            command: cmd,
            user_name: std::env::var("USER").unwrap_or("daemon".to_string()),
            log_dir: "/tmp/rqd".to_string(),
            show: "show".to_string(),
            shot: "shot".to_string(),
            job_temp_dir: "deprecated".to_string(),
            frame_temp_dir: "/tmp".to_string(),
            log_file: "deprecated".to_string(),
            log_dir_file: "deprecated".to_string(),
            start_time: 0,
            num_cores: 200,
            gid: 10,
            ignore_nimby: false,
            environment: env_vars,
            attributes: HashMap::new(),
            num_gpus: 0,
            children: None,
            uid_optional: match uid {
                Some(uid) => Some(UidOptional::Uid(uid as i32)),
                None => None,
            },
        };

        let mut client = self.client.lock().await;
        let mut request = pb::RqdStaticLaunchFrameRequest::default();
        request.run_frame = Some(run_frame);
        client
            .launch_frame(request)
            .await
            .into_diagnostic()
            .and(Ok(()))
    }
}
