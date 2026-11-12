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
use opencue_proto::facility::{
    AllocCreateRequest, AllocDeleteRequest, AllocGetAllRequest, AllocGetHostsRequest,
    AllocReparentHostsRequest, AllocSetNameRequest, AllocSetTagRequest, FacilityGetRequest,
};
use opencue_proto::host::HostSeq;

use super::Context;
use crate::cli::AllocCommand;
use crate::client::{required, rpc_error};
use crate::output;

/// Runs an `alloc` subcommand.
pub async fn run(ctx: &Context, cmd: AllocCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    match cmd {
        AllocCommand::List => {
            let allocations = cuebot
                .allocation()
                .get_all(AllocGetAllRequest {})
                .await
                .map_err(rpc_error("listing allocations"))?
                .into_inner()
                .allocations
                .unwrap_or_default()
                .allocations;
            print!("{}", output::allocations(&allocations));
        }
        AllocCommand::Create {
            facility,
            name,
            tag,
        } => {
            if !ctx.confirm(&format!(
                "Create new allocation {facility}.{name}, with tag {tag}"
            ))? {
                return Ok(());
            }
            let found = cuebot
                .facility()
                .get(FacilityGetRequest {
                    name: facility.clone(),
                })
                .await
                .map_err(rpc_error(format!("finding facility '{facility}'")))?
                .into_inner()
                .facility;
            let created = cuebot
                .allocation()
                .create(AllocCreateRequest {
                    name: name.clone(),
                    tag,
                    facility: Some(required(found, "facility")?),
                })
                .await
                .map_err(rpc_error(format!("creating allocation '{name}'")))?
                .into_inner()
                .allocation;
            println!(
                "Created allocation: {}",
                required(created, "allocation")?.name
            );
        }
        AllocCommand::Delete { alloc } => {
            let found = cuebot.find_allocation(&alloc).await?;
            if ctx.confirm(&format!("Delete allocation {alloc}"))? {
                cuebot
                    .allocation()
                    .delete(AllocDeleteRequest {
                        allocation: Some(found),
                    })
                    .await
                    .map_err(rpc_error(format!("deleting allocation '{alloc}'")))?;
            }
        }
        AllocCommand::Rename { alloc, new_name } => {
            let new_name = strip_facility(&new_name).to_string();
            let found = cuebot.find_allocation(&alloc).await?;
            if ctx.confirm(&format!("Rename allocation from {alloc} to {new_name}"))? {
                cuebot
                    .allocation()
                    .set_name(AllocSetNameRequest {
                        allocation: Some(found),
                        name: new_name,
                    })
                    .await
                    .map_err(rpc_error(format!("renaming allocation '{alloc}'")))?;
            }
        }
        AllocCommand::Transfer { src, dst } => {
            let src_alloc = cuebot.find_allocation(&src).await?;
            let dst_alloc = cuebot.find_allocation(&dst).await?;
            if !ctx.confirm(&format!(
                "Transfer hosts from {} to {}",
                src_alloc.name, dst_alloc.name
            ))? {
                return Ok(());
            }
            let hosts = cuebot
                .allocation()
                .get_hosts(AllocGetHostsRequest {
                    allocation: Some(src_alloc),
                })
                .await
                .map_err(rpc_error(format!("listing hosts of '{src}'")))?
                .into_inner()
                .hosts
                .unwrap_or_default();
            cuebot
                .allocation()
                .reparent_hosts(AllocReparentHostsRequest {
                    allocation: Some(dst_alloc),
                    hosts: Some(HostSeq { hosts: hosts.hosts }),
                })
                .await
                .map_err(rpc_error(format!("moving hosts into '{dst}'")))?;
        }
        AllocCommand::Tag { alloc, tag } => {
            let found = cuebot.find_allocation(&alloc).await?;
            if ctx.confirm(&format!("Re-tag allocation {alloc} with {tag}"))? {
                cuebot
                    .allocation()
                    .set_tag(AllocSetTagRequest {
                        allocation: Some(found),
                        tag,
                    })
                    .await
                    .map_err(rpc_error(format!("tagging allocation '{alloc}'")))?;
            }
        }
    }
    Ok(())
}

/// Drops a leading `facility.` from an allocation name, since renames keep the facility.
fn strip_facility(name: &str) -> &str {
    name.split_once('.').map_or(name, |(_, rest)| rest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_facility_prefix() {
        assert_eq!(strip_facility("local.general"), "general");
        assert_eq!(strip_facility("general"), "general");
    }
}
