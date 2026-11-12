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
use opencue_proto::service::ServiceGetDefaultServicesRequest;
use opencue_proto::show::ShowGetServiceOverridesRequest;

use super::Context;
use crate::cli::ServiceCommand;
use crate::client::rpc_error;
use crate::output;

/// Runs a `service` subcommand.
pub async fn run(ctx: &Context, cmd: ServiceCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    let ServiceCommand::List { show } = cmd;
    let services = match show {
        Some(name) => {
            let show = cuebot.find_show(&name).await?;
            cuebot
                .show()
                .get_service_overrides(ShowGetServiceOverridesRequest { show: Some(show) })
                .await
                .map_err(rpc_error(format!("listing service overrides of '{name}'")))?
                .into_inner()
                .service_overrides
                .unwrap_or_default()
                .service_overrides
                .into_iter()
                .filter_map(|o| o.data)
                .collect()
        }
        None => {
            cuebot
                .service()
                .get_default_services(ServiceGetDefaultServicesRequest {})
                .await
                .map_err(rpc_error("listing default services"))?
                .into_inner()
                .services
                .unwrap_or_default()
                .services
        }
    };
    print!("{}", output::services(&services));
    Ok(())
}
