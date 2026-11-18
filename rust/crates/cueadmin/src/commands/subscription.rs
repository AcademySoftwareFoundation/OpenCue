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

use super::Context;
use crate::cli::SubscriptionCommand;
use crate::client::rpc_error;
use crate::criteria::cores_to_units;
use crate::format::format_num;
use crate::output;
use crate::table::Table;
use miette::{bail, Result};
use opencue_proto::facility::AllocGetSubscriptionsRequest;
use opencue_proto::show::{ShowCreateSubscriptionRequest, ShowGetSubscriptionRequest};
use opencue_proto::subscription::{
    SubscriptionDeleteRequest, SubscriptionSetBurstRequest, SubscriptionSetSizeRequest,
};

/// Runs a `subscription` subcommand.
pub async fn run(ctx: &Context, cmd: SubscriptionCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    match cmd {
        SubscriptionCommand::List {
            alloc: Some(alloc), ..
        } => {
            let found = cuebot.find_allocation(&alloc).await?;
            let subs = cuebot
                .allocation()
                .get_subscriptions(AllocGetSubscriptionsRequest {
                    allocation: Some(found),
                })
                .await
                .map_err(rpc_error(format!("listing subscriptions of '{alloc}'")))?
                .into_inner()
                .subscriptions
                .unwrap_or_default()
                .subscriptions;
            ctx.out.table(&output::subscriptions(&subs, &alloc), false);
        }
        SubscriptionCommand::List { shows, alloc: None } => {
            // Pretty prints a table per show; raw prints them as one, under a single header.
            let mut combined: Option<Table> = None;
            for name in &shows {
                let show = match cuebot.find_show(name).await {
                    Ok(show) => show,
                    Err(e) => {
                        eprintln!("Warning: skipping {name}: {e}");
                        continue;
                    }
                };
                let subs = cuebot
                    .show()
                    .get_subscriptions(ShowGetSubscriptionRequest { show: Some(show) })
                    .await
                    .map_err(rpc_error(format!("listing subscriptions of '{name}'")))?
                    .into_inner()
                    .subscriptions
                    .unwrap_or_default()
                    .subscriptions;
                let table = output::subscriptions(&subs, name);
                match &mut combined {
                    Some(all) if ctx.out.raw => all.extend(table),
                    Some(_) => {
                        println!();
                        ctx.out.table(&table, false);
                    }
                    None => {
                        if !ctx.out.raw {
                            ctx.out.table(&table, false);
                        }
                        combined = Some(table);
                    }
                }
            }
            match combined {
                Some(all) if ctx.out.raw => ctx.out.table(&all, false),
                Some(_) => {}
                None => {
                    bail!("none of the given shows exist: {}", shows.join(", "));
                }
            }
        }
        SubscriptionCommand::Create {
            show,
            alloc,
            size,
            burst,
        } => {
            let found_show = cuebot.find_show(&show).await?;
            let found_alloc = cuebot.find_allocation(&alloc).await?;
            if ctx.confirm(&format!("Create subscription for {show} on {alloc}"))? {
                cuebot
                    .show()
                    .create_subscription(ShowCreateSubscriptionRequest {
                        show: Some(found_show),
                        allocation_id: found_alloc.id,
                        size,
                        burst,
                    })
                    .await
                    .map_err(rpc_error(format!("subscribing '{show}' to '{alloc}'")))?;
                ctx.out.done(format!(
                    "Subscribed {show} to {alloc} with {size} cores, bursting to {burst}"
                ));
            }
        }
        SubscriptionCommand::Delete { show, alloc } => {
            let sub = cuebot.find_subscription(&show, &alloc).await?;
            if ctx.confirm(&format!("Delete {show}'s subscription to {alloc}"))? {
                cuebot
                    .subscription()
                    .delete(SubscriptionDeleteRequest {
                        subscription: Some(sub),
                    })
                    .await
                    .map_err(rpc_error(format!("deleting subscription of '{show}'")))?;
                ctx.out
                    .done(format!("Deleted {show}'s subscription to {alloc}"));
            }
        }
        SubscriptionCommand::Size { show, alloc, cores } => {
            let sub = cuebot.find_subscription(&show, &alloc).await?;
            let new_size = cores_to_units(cores);
            if !ctx.confirm(&format!(
                "Set the size of {show}'s subscription to {alloc} from {} to {} cores",
                units_to_cores(sub.size),
                units_to_cores(new_size)
            ))? {
                return Ok(());
            }
            cuebot
                .subscription()
                .set_size(SubscriptionSetSizeRequest {
                    subscription: Some(sub),
                    new_size,
                })
                .await
                .map_err(rpc_error(format!("resizing subscription of '{show}'")))?;
            ctx.out.done(format!(
                "Set the size of {show}'s subscription to {alloc} to {} cores",
                units_to_cores(new_size)
            ));
        }
        SubscriptionCommand::Burst { show, alloc, burst } => {
            let sub = cuebot.find_subscription(&show, &alloc).await?;
            let burst = burst.to_core_units(sub.size);
            if !ctx.confirm(&format!(
                "Set the burst of {show}'s subscription to {alloc} from {} to {} cores",
                units_to_cores(sub.burst),
                units_to_cores(burst)
            ))? {
                return Ok(());
            }
            cuebot
                .subscription()
                .set_burst(SubscriptionSetBurstRequest {
                    subscription: Some(sub),
                    burst,
                })
                .await
                .map_err(rpc_error(format!("setting burst of '{show}'")))?;
            ctx.out.done(format!(
                "Set the burst of {show}'s subscription to {alloc} to {} cores",
                units_to_cores(burst)
            ));
        }
    }
    Ok(())
}

fn units_to_cores(units: i32) -> String {
    format_num(units as f64 / 100.0)
}
