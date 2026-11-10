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

use miette::Result;
use opencue_proto::depend::DependSatisfyRequest;
use opencue_proto::job::{
    FrameSearchCriteria, FrameState, FrameStateSeq, Job, JobGetWhatThisDependsOnRequest,
    JobKillRequest, JobPauseRequest, JobResumeRequest, JobRetryFramesRequest, JobSearchCriteria,
    JobSetMaxCoresRequest, JobSetMinCoresRequest, JobSetPriorityRequest,
};
use tracing::debug;

use super::Context;
use crate::cli::JobCommand;
use crate::client::rpc_error;
use crate::output;

/// Runs a `job` subcommand.
pub async fn run(ctx: &Context, cmd: JobCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    match cmd {
        JobCommand::List { matches, long } => {
            let jobs = cuebot
                .get_jobs(JobSearchCriteria {
                    substr: matches,
                    ..Default::default()
                })
                .await?;
            if long {
                print!("{}", output::jobs(&jobs));
            } else {
                for job in jobs {
                    println!("{}", job.name);
                }
            }
        }
        JobCommand::Pause { jobs } => {
            for name in jobs {
                let job = cuebot.find_job(&name).await?;
                debug!("pausing job {name}");
                cuebot
                    .job()
                    .pause(JobPauseRequest { job: Some(job) })
                    .await
                    .map_err(rpc_error(format!("pausing '{name}'")))?;
            }
        }
        JobCommand::Resume { jobs } => {
            for name in jobs {
                let job = cuebot.find_job(&name).await?;
                debug!("resuming job {name}");
                cuebot
                    .job()
                    .resume(JobResumeRequest { job: Some(job) })
                    .await
                    .map_err(rpc_error(format!("resuming '{name}'")))?;
            }
        }
        JobCommand::Kill { jobs, all, reason } => {
            let prompt = if all {
                "Kill ALL jobs".to_string()
            } else {
                format!("Kill {} job(s)", jobs.len())
            };
            if !ctx.confirm(&prompt)? {
                return Ok(());
            }
            let reason = reason.unwrap_or_default();
            for job in targets(ctx, jobs, all).await? {
                debug!("killing job {}", job.name);
                let name = job.name.clone();
                cuebot
                    .job()
                    .kill(kill_request(job, &reason))
                    .await
                    .map_err(rpc_error(format!("killing '{name}'")))?;
            }
        }
        JobCommand::Retry { jobs, all } => {
            let prompt = if all {
                "Retry dead frames for ALL jobs".to_string()
            } else {
                format!("Retry dead frames for {} job(s)", jobs.len())
            };
            if !ctx.confirm(&prompt)? {
                return Ok(());
            }
            for job in targets(ctx, jobs, all).await? {
                debug!("retrying dead frames of {}", job.name);
                let name = job.name.clone();
                cuebot
                    .job()
                    .retry_frames(JobRetryFramesRequest {
                        job: Some(job),
                        req: Some(dead_frames()),
                    })
                    .await
                    .map_err(rpc_error(format!("retrying frames of '{name}'")))?;
            }
        }
        JobCommand::DropDepends { jobs } => {
            if !ctx.confirm(&format!("Drop all dependencies for {} job(s)", jobs.len()))? {
                return Ok(());
            }
            for name in jobs {
                drop_depends(ctx, &name).await?;
            }
        }
        JobCommand::MinCores { job, cores } => {
            let found = cuebot.find_job(&job).await?;
            if ctx.confirm(&format!("Set min cores for {job} to {cores:.2}"))? {
                cuebot
                    .job()
                    .set_min_cores(JobSetMinCoresRequest {
                        job: Some(found),
                        val: cores,
                    })
                    .await
                    .map_err(rpc_error(format!("setting min cores of '{job}'")))?;
            }
        }
        JobCommand::MaxCores { job, cores } => {
            let found = cuebot.find_job(&job).await?;
            if ctx.confirm(&format!("Set max cores for {job} to {cores:.2}"))? {
                cuebot
                    .job()
                    .set_max_cores(JobSetMaxCoresRequest {
                        job: Some(found),
                        val: cores,
                    })
                    .await
                    .map_err(rpc_error(format!("setting max cores of '{job}'")))?;
            }
        }
        JobCommand::Priority { job, priority } => {
            let found = cuebot.find_job(&job).await?;
            if ctx.confirm(&format!("Set priority for {job} to {priority}"))? {
                cuebot
                    .job()
                    .set_priority(JobSetPriorityRequest {
                        job: Some(found),
                        val: priority,
                    })
                    .await
                    .map_err(rpc_error(format!("setting priority of '{job}'")))?;
            }
        }
    }
    Ok(())
}

/// Returns every active job when `all` is set, otherwise looks up `names`.
async fn targets(ctx: &Context, names: Vec<String>, all: bool) -> Result<Vec<Job>> {
    if all {
        return ctx.cuebot.get_jobs(JobSearchCriteria::default()).await;
    }
    let mut jobs = Vec::with_capacity(names.len());
    for name in names {
        jobs.push(ctx.cuebot.find_job(&name).await?);
    }
    Ok(jobs)
}

async fn drop_depends(ctx: &Context, name: &str) -> Result<()> {
    let job = ctx.cuebot.find_job(name).await?;
    let depends = ctx
        .cuebot
        .job()
        .get_what_this_depends_on(JobGetWhatThisDependsOnRequest { job: Some(job) })
        .await
        .map_err(rpc_error(format!("listing dependencies of '{name}'")))?
        .into_inner()
        .depends
        .unwrap_or_default()
        .depends;
    for depend in depends {
        debug!("dropping depend {} of {name}", depend.id);
        ctx.cuebot
            .depend()
            .satisfy(DependSatisfyRequest {
                depend: Some(depend),
            })
            .await
            .map_err(rpc_error(format!("dropping a dependency of '{name}'")))?;
    }
    Ok(())
}

/// Builds a kill request recording who killed the job, from where.
fn kill_request(job: Job, reason: &str) -> JobKillRequest {
    JobKillRequest {
        job: Some(job),
        username: whoami::username(),
        pid: std::process::id().to_string(),
        host_kill: whoami::fallible::hostname().unwrap_or_default(),
        reason: reason.to_string(),
    }
}

fn dead_frames() -> FrameSearchCriteria {
    FrameSearchCriteria {
        states: Some(FrameStateSeq {
            frame_states: vec![FrameState::Dead as i32],
        }),
        page: 1,
        ..Default::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn retry_only_targets_dead_frames() {
        let criteria = dead_frames();
        assert_eq!(
            criteria.states.unwrap().frame_states,
            [FrameState::Dead as i32]
        );
    }

    #[test]
    fn kill_records_the_caller() {
        let request = kill_request(Job::default(), "bad submission");
        assert_eq!(request.pid, std::process::id().to_string());
        assert_eq!(request.reason, "bad submission");
        assert!(!request.username.is_empty());
    }
}
