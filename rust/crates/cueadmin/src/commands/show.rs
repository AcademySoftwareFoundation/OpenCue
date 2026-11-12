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
use opencue_proto::show::{
    ShowArchiveRequest, ShowCreateShowRequest, ShowDeleteRequest, ShowEnableBookingRequest,
    ShowEnableDispatchingRequest, ShowGetShowsRequest, ShowSetActiveRequest,
    ShowSetDefaultMaxCoresRequest, ShowSetDefaultMinCoresRequest, ShowSetSchedulerManagedRequest,
};

use super::Context;
use crate::cli::ShowCommand;
use crate::client::rpc_error;
use crate::output;

/// Runs a `show` subcommand.
pub async fn run(ctx: &Context, cmd: ShowCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    match cmd {
        ShowCommand::List => {
            let shows = cuebot
                .show()
                .get_shows(ShowGetShowsRequest {})
                .await
                .map_err(rpc_error("listing shows"))?
                .into_inner()
                .shows
                .unwrap_or_default()
                .shows;
            print!("{}", output::shows(&shows));
        }
        ShowCommand::Create { show } => {
            if ctx.confirm(&format!("Create new show {show}"))? {
                cuebot
                    .show()
                    .create_show(ShowCreateShowRequest { name: show.clone() })
                    .await
                    .map_err(rpc_error(format!("creating show '{show}'")))?;
            }
        }
        ShowCommand::Delete { show } => {
            let found = cuebot.find_show(&show).await?;
            if ctx.confirm(&format!("Delete show {show}"))? {
                cuebot
                    .show()
                    .delete(ShowDeleteRequest { show: Some(found) })
                    .await
                    .map_err(rpc_error(format!("deleting show '{show}'")))?;
            }
        }
        ShowCommand::Enable { show } => set_active(ctx, &show, true).await?,
        ShowCommand::Disable { show } => set_active(ctx, &show, false).await?,
        ShowCommand::Dispatching { show, enabled } => {
            let found = cuebot.find_show(&show).await?;
            if enabled || ctx.confirm(&format!("Disable dispatching on {show}"))? {
                cuebot
                    .show()
                    .enable_dispatching(ShowEnableDispatchingRequest {
                        show: Some(found),
                        enabled,
                    })
                    .await
                    .map_err(rpc_error(format!("changing dispatching on '{show}'")))?;
            }
        }
        ShowCommand::Booking { show, enabled } => {
            let found = cuebot.find_show(&show).await?;
            if enabled || ctx.confirm(&format!("Disable booking on {show}"))? {
                cuebot
                    .show()
                    .enable_booking(ShowEnableBookingRequest {
                        show: Some(found),
                        enabled,
                    })
                    .await
                    .map_err(rpc_error(format!("changing booking on '{show}'")))?;
            }
        }
        ShowCommand::DefaultMinCores { show, cores } => {
            let found = cuebot.find_show(&show).await?;
            if ctx.confirm(&format!("Set the default min cores of {show} to {cores}"))? {
                cuebot
                    .show()
                    .set_default_min_cores(ShowSetDefaultMinCoresRequest {
                        show: Some(found),
                        min_cores: cores,
                    })
                    .await
                    .map_err(rpc_error(format!("setting default min cores on '{show}'")))?;
            }
        }
        ShowCommand::DefaultMaxCores { show, cores } => {
            let found = cuebot.find_show(&show).await?;
            if ctx.confirm(&format!("Set the default max cores of {show} to {cores}"))? {
                cuebot
                    .show()
                    .set_default_max_cores(ShowSetDefaultMaxCoresRequest {
                        show: Some(found),
                        max_cores: cores,
                    })
                    .await
                    .map_err(rpc_error(format!("setting default max cores on '{show}'")))?;
            }
        }
        ShowCommand::Archive { show, target } => {
            let found = cuebot.find_show(&show).await?;
            // Fail early if the target doesn't exist.
            cuebot.find_show(&target).await?;
            if ctx.confirm(&format!("Archive show {show} to {target}"))? {
                cuebot
                    .show()
                    .archive(ShowArchiveRequest {
                        show: Some(found),
                        target_show_name: target,
                    })
                    .await
                    .map_err(rpc_error(format!("archiving show '{show}'")))?;
            }
        }
        ShowCommand::SchedulerManaged { show, enabled } => {
            let found = cuebot.find_show(&show).await?;
            let verb = if enabled { "Enable" } else { "Disable" };
            if ctx.confirm(&format!("{verb} scheduler-managed accounting on {show}"))? {
                cuebot
                    .show()
                    .set_scheduler_managed(ShowSetSchedulerManagedRequest {
                        show: Some(found),
                        enabled,
                    })
                    .await
                    .map_err(rpc_error(format!("changing scheduler-managed on '{show}'")))?;
            }
        }
    }
    Ok(())
}

async fn set_active(ctx: &Context, show: &str, active: bool) -> Result<()> {
    let found = ctx.cuebot.find_show(show).await?;
    let verb = if active { "Enable" } else { "Disable" };
    if ctx.confirm(&format!("{verb} show {show}"))? {
        ctx.cuebot
            .show()
            .set_active(ShowSetActiveRequest {
                show: Some(found),
                value: active,
            })
            .await
            .map_err(rpc_error(format!("changing active state of '{show}'")))?;
    }
    Ok(())
}
