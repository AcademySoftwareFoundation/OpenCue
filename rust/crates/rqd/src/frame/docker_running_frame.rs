use std::{cmp, sync::Arc};

use bollard::{
    Docker,
    container::{
        self, AttachContainerOptions, AttachContainerResults, CreateContainerOptions,
        StartContainerOptions, WaitContainerOptions,
    },
    secret::{
        ContainerWaitResponse, DeviceMapping, HostConfig, Mount, MountBindOptions,
        MountBindOptionsPropagationEnum, MountTypeEnum,
    },
};
use futures::StreamExt;
use itertools::Either;
use tokio::io::AsyncReadExt;
use tracing::{error, info, trace, warn};

use crate::frame::frame_cmd::FrameCmdBuilder;
use crate::frame::running_frame::RunningFrame;

use miette::{Context, IntoDiagnostic, Result, miette};

use super::logging::{FrameLogger, FrameLoggerBuilder};

impl RunningFrame {
    /// Runs the frame as a docker container.
    ///
    /// This method is the main entry point for executing a frame. It:
    /// 1. Creates a logger for the frame
    /// 2. Runs the frame command on a new process
    /// 3. Updates the frame's exit code based on the result
    /// 4. Cleans up any snapshots created during execution
    ///
    /// If the process fails to spawn, it logs the error but doesn't set an exit code.
    /// The method handles both successful and failed execution scenarios.
    pub async fn run_docker(&self, recover_mode: bool) {
        let logger_base = FrameLoggerBuilder::from_logger_config(
            self.log_path.clone(),
            &self.config,
            self.config.run_as_user.then(|| (self.uid, self.gid)),
        );
        if let Err(err) = logger_base {
            error!("Failed to create log stream for {}: {}", self.log_path, err);
            if let Err(err) = self.fail_before_start() {
                error!("Failed to mark frame {} as finished. {}", self, err);
            }
            return;
        }
        let logger = Arc::new(logger_base.unwrap());

        let exit_code = if recover_mode {
            match self.recover_inner(Arc::clone(&logger)).await {
                Ok((exit_code, exit_signal)) => {
                    if let Err(err) = self.finish(exit_code, exit_signal) {
                        warn!("Failed to mark frame {} as finished. {}", self, err);
                    }
                    logger.writeln(&self.write_footer());
                    Some(exit_code)
                }
                Err(err) => {
                    let msg = format!("Frame {} failed to be recovered. {}", self.to_string(), err);
                    logger.writeln(&msg);
                    error!(msg);
                    None
                }
            }
        } else {
            let run_result = self.run_docker_inner(Arc::clone(&logger)).await;
            match run_result {
                Ok((exit_code, exit_signal)) => {
                    if let Err(err) = self.finish(exit_code, exit_signal) {
                        warn!("Failed to mark frame {} as finished. {}", self, err);
                    }
                    logger.writeln(&self.write_footer());
                    Some(exit_code)
                }
                Err(err) => {
                    let msg = format!("Frame {} failed to be spawned. {}", self.to_string(), err);
                    logger.writeln(&msg);
                    error!(msg);
                    if let Err(err) = self.fail_before_start() {
                        error!("Failed to mark frame {} as finished. {}", self, err);
                    }
                    None
                }
            }
        };
        if let Err(err) = self.clear_snapshot().await {
            // Only warn if a job was actually launched
            if exit_code.is_some() {
                warn!(
                    "Failed to clear snapshot {}: {}",
                    self.snapshot_path().unwrap_or("empty_path".to_string()),
                    err
                );
            }
        };
    }

    fn interprete_output_docker(wait_response: ContainerWaitResponse) -> (i32, Option<i32>) {
        let exit_signal = None;
        let exit_code = wait_response.status_code as i32;

        // If the cmd wrapper interprets the signal as an output, 128 needs to be subtracted
        // from the code to recover the received signal
        if exit_code > 128 {
            exit_code = 1;
            exit_signal = Some(exit_code - 128);
        }
        (exit_code, exit_signal)
    }

    pub async fn run_docker_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        logger.writeln(self.write_header().as_str());

        let docker = Docker::connect_with_socket_defaults()
            .into_diagnostic()
            .wrap_err("Failed to connect to docker socket.")?;

        let image = Some(self.config.get_docker_image(&self.request.os));
        let env: Option<Vec<String>> = Some(
            self.env_vars
                .iter()
                .map(|(k, v)| format!("{k}={v}"))
                .collect(),
        );
        let working_dir = Some(self.config.temp_path.clone());

        // Build Command
        let mut command =
            FrameCmdBuilder::new(&self.config.shell_path, self.entrypoint_file_path.clone());
        if self.config.desktop_mode {
            command.with_nice();
        }
        if let Some(cpu_list) = &self.thread_ids {
            command.with_taskset(cpu_list.clone());
        }

        command.with_become_user(self.uid, self.gid, self.request.user_name.clone());
        let (_cmd, cmd_str) = command
            .with_frame_cmd(self.request.command.clone())
            .with_exit_file(self.exit_file_path.clone())
            .build()?;
        let entrypoint = Some(vec![
            // Execute entrypoint file
            self.entrypoint_file_path.clone(),
        ]);

        trace!("Running {}: {}", self.entrypoint_file_path, cmd_str);
        logger.writeln(format!("Running {}:", self.entrypoint_file_path).as_str());

        let host_config = self.build_docker_host_config();
        let container_name = format!(
            "frame_{}_{}",
            self.request.job_name, self.request.resource_id
        );

        let _container = &docker
            .create_container(
                Some(CreateContainerOptions {
                    name: container_name.clone(),
                    platform: None,
                }),
                container::Config::<String> {
                    hostname: Some(self.hostname.clone()),
                    attach_stdout: Some(true),
                    attach_stderr: Some(true),
                    tty: Some(true),
                    env,
                    image,
                    working_dir,
                    entrypoint,
                    host_config: Some(host_config),
                    ..Default::default()
                },
            )
            .await
            .into_diagnostic()
            .wrap_err("Failed to create container")?;

        let _ = &docker
            .start_container(&container_name, None::<StartContainerOptions<String>>)
            .await
            .into_diagnostic()
            .wrap_err("Failed to start container")?;

        let AttachContainerResults {
            output: mut log_stream,
            input: _,
        } = docker
            .attach_container(
                &container_name,
                Some(AttachContainerOptions::<String> {
                    stdin: Some(false),
                    stdout: Some(true),
                    stderr: Some(true),
                    stream: Some(true),
                    logs: Some(true),
                    detach_keys: Some("ctrl-c".to_string()),
                }),
            )
            .await
            .into_diagnostic()?;
        // Read the pid from from first line of the log
        let first_line = log_stream
            .next()
            .await
            .ok_or_else(|| miette!("Failed to attach to log stream"))?;

        let pid_result = first_line
            .into_diagnostic()
            .wrap_err("Failed to read pid from log")
            .and_then(|line| line.to_string().parse::<u32>().into_diagnostic());

        let pid = match pid_result {
            Ok(pid) => pid,
            Err(err) => {
                // Clean up container before returning the error
                let _ = docker.remove_container(&container_name, None).await;
                return Err(err);
            }
        };

        // Update frame state with frame pid
        self.start(pid);

        info!(
            "Frame {self} started with pid {pid}, with taskset {}",
            self.taskset()
        );

        let _ = self.create_snapshot().await;
        let log_watcher_handle = tokio::task::spawn(async move {
            while let Some(Ok(output)) = log_stream.next().await {
                logger.write(output.into_bytes().as_ref());
            }
        });

        let output_stream =
            docker.wait_container(&container_name, None::<WaitContainerOptions<String>>);
        let mut exit_code = 1;
        let mut exit_signal = None;
        if let Some(Ok(output)) = output_stream.take(1).next().await {
            (exit_code, exit_signal) = Self::interprete_output_docker(Either::Right(output));
        }
        log_watcher_handle.abort();

        let msg = match exit_code {
            0 => format!("Frame {}(pid={}) finished successfully", self, pid),
            _ => format!(
                "Frame {}(pid={}) finished with exit_code={} and exit_signal={}. Log: {}",
                self,
                pid,
                exit_code,
                exit_signal.unwrap_or(0),
                self.log_path,
            ),
        };
        info!(msg);

        Ok((exit_code, exit_signal))
    }

    pub fn build_docker_host_config(&self) -> HostConfig {
        let mounts = Some(
            self.config
                .docker_mounts
                .iter()
                .map(|mount| Mount {
                    target: Some(mount.target.clone()),
                    source: Some(mount.source.clone()),
                    typ: Some(
                        MountTypeEnum::from_str(mount.typ.as_str()).unwrap_or(MountTypeEnum::BIND),
                    ),
                    bind_options: Some(MountBindOptions {
                        propagation: Some(
                            MountBindOptionsPropagationEnum::from_str(
                                &mount.bind_propagation.as_str(),
                            )
                            .unwrap_or(MountBindOptionsPropagationEnum::SLAVE),
                        ),
                        ..Default::default()
                    }),

                    ..Default::default()
                })
                .collect(),
        );

        // Docker requires memory limits higer than 6MG
        let soft_memory_limit = cmp::max(self.request.soft_memory_limit, 6291456) * 1000;
        let hard_memory_limit = cmp::max(self.request.hard_memory_limit, 6291456) * 1000;
        HostConfig {
            devices: Some(vec![DeviceMapping {
                path_on_host: Some("/dev/fuse".to_string()),
                path_in_container: Some("/dev/fuse".to_string()),
                cgroup_permissions: None,
            }]),
            auto_remove: Some(true),
            mounts,
            privileged: Some(true),
            memory_reservation: Some(soft_memory_limit),
            memory: Some(hard_memory_limit),
            ..Default::default()
        }
    }
}
