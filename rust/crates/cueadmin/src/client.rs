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

//! gRPC connection to Cuebot and lookups shared by the commands.

use std::fmt::Display;

use miette::{miette, Result};
use opencue_proto::depend::depend_interface_client::DependInterfaceClient;
use opencue_proto::facility::allocation_interface_client::AllocationInterfaceClient;
use opencue_proto::facility::facility_interface_client::FacilityInterfaceClient;
use opencue_proto::facility::{AllocFindRequest, Allocation};
use opencue_proto::host::host_interface_client::HostInterfaceClient;
use opencue_proto::host::proc_interface_client::ProcInterfaceClient;
use opencue_proto::host::{Host, HostGetHostsRequest, HostSearchCriteria};
use opencue_proto::job::job_interface_client::JobInterfaceClient;
use opencue_proto::job::{Job, JobFindJobRequest, JobGetJobsRequest, JobSearchCriteria};
use opencue_proto::service::service_interface_client::ServiceInterfaceClient;
use opencue_proto::show::show_interface_client::ShowInterfaceClient;
use opencue_proto::show::{Show, ShowFindShowRequest};
use opencue_proto::subscription::subscription_interface_client::SubscriptionInterfaceClient;
use opencue_proto::subscription::{Subscription, SubscriptionFindRequest};
use rand::seq::SliceRandom;
use tonic::transport::{Channel, Endpoint};
use tonic::Status;
use tracing::{debug, warn};

use crate::config::Config;

/// A connection to one Cuebot.
pub struct Cuebot {
    channel: Channel,
    max_message_bytes: usize,
}

macro_rules! clients {
    ($($(#[$doc:meta])* $name:ident: $client:ident;)*) => {
        $(
            $(#[$doc])*
            pub fn $name(&self) -> $client<Channel> {
                $client::new(self.channel.clone())
                    .max_decoding_message_size(self.max_message_bytes)
                    .max_encoding_message_size(self.max_message_bytes)
            }
        )*
    };
}

impl Cuebot {
    /// Connects to the first reachable host of `hosts`, trying them in random order to spread
    /// load across Cuebots.
    pub async fn connect(hosts: &[String], config: &Config) -> Result<Self> {
        let mut hosts = hosts.to_vec();
        hosts.shuffle(&mut rand::thread_rng());
        for host in &hosts {
            debug!("connecting to Cuebot at {host}");
            let endpoint = Endpoint::from_shared(format!("http://{host}"))
                .map_err(|e| miette!("invalid Cuebot address '{host}': {e}"))?
                .connect_timeout(config.timeout)
                .timeout(config.timeout);
            match endpoint.connect().await {
                Ok(channel) => {
                    return Ok(Self {
                        channel,
                        max_message_bytes: config.max_message_bytes,
                    })
                }
                Err(e) => warn!("could not connect to Cuebot at {host}: {}", error_chain(&e)),
            }
        }
        Err(miette!(
            help = "check --server, CUEBOT_HOSTS or the facility in your opencue config",
            "could not connect to any Cuebot: {}",
            hosts.join(", ")
        ))
    }

    clients! {
        /// Allocation service.
        allocation: AllocationInterfaceClient;
        /// Depend service.
        depend: DependInterfaceClient;
        /// Facility service.
        facility: FacilityInterfaceClient;
        /// Host service.
        host: HostInterfaceClient;
        /// Job service.
        job: JobInterfaceClient;
        /// Proc service.
        proc: ProcInterfaceClient;
        /// Service service.
        service: ServiceInterfaceClient;
        /// Show service.
        show: ShowInterfaceClient;
        /// Subscription service.
        subscription: SubscriptionInterfaceClient;
    }

    /// Finds a show by name.
    pub async fn find_show(&self, name: &str) -> Result<Show> {
        let response = self
            .show()
            .find_show(ShowFindShowRequest { name: name.into() })
            .await
            .map_err(rpc_error(format!("finding show '{name}'")))?;
        required(response.into_inner().show, "show")
    }

    /// Finds an allocation by its `facility.name`.
    pub async fn find_allocation(&self, name: &str) -> Result<Allocation> {
        let response = self
            .allocation()
            .find(AllocFindRequest { name: name.into() })
            .await
            .map_err(rpc_error(format!("finding allocation '{name}'")))?;
        required(response.into_inner().allocation, "allocation")
    }

    /// Finds an active job by name.
    pub async fn find_job(&self, name: &str) -> Result<Job> {
        let response = self
            .job()
            .find_job(JobFindJobRequest { name: name.into() })
            .await
            .map_err(rpc_error(format!("finding job '{name}'")))?;
        required(response.into_inner().job, "job")
    }

    /// Finds the subscription of `show` to `alloc`.
    pub async fn find_subscription(&self, show: &str, alloc: &str) -> Result<Subscription> {
        let name = format!("{alloc}.{show}");
        let response = self
            .subscription()
            .find(SubscriptionFindRequest { name })
            .await
            .map_err(rpc_error(format!(
                "finding subscription of '{show}' to '{alloc}'"
            )))?;
        required(response.into_inner().subscription, "subscription")
    }

    /// Returns the hosts matching `criteria`.
    pub async fn get_hosts(&self, criteria: HostSearchCriteria) -> Result<Vec<Host>> {
        let response = self
            .host()
            .get_hosts(HostGetHostsRequest { r: Some(criteria) })
            .await
            .map_err(rpc_error("listing hosts"))?;
        Ok(response.into_inner().hosts.unwrap_or_default().hosts)
    }

    /// Returns the active jobs matching `criteria`.
    pub async fn get_jobs(&self, criteria: JobSearchCriteria) -> Result<Vec<Job>> {
        let response = self
            .job()
            .get_jobs(JobGetJobsRequest { r: Some(criteria) })
            .await
            .map_err(rpc_error("listing jobs"))?;
        Ok(response.into_inner().jobs.unwrap_or_default().jobs)
    }
}

/// Joins an error with its sources, since tonic's transport errors only say "transport error".
fn error_chain(error: &dyn std::error::Error) -> String {
    let mut message = error.to_string();
    let mut source = error.source();
    while let Some(cause) = source {
        message.push_str(": ");
        message.push_str(&cause.to_string());
        source = cause.source();
    }
    message
}

/// Builds a `map_err` adapter that turns a gRPC status into an error naming what was attempted.
pub fn rpc_error(action: impl Display) -> impl FnOnce(Status) -> miette::Report {
    move |status| {
        let message = status.message().trim();
        let message = if message.is_empty() {
            status.code().description()
        } else {
            message
        };
        miette!("{action} failed: {message}")
    }
}

/// Unwraps an optional message field of a response.
pub fn required<T>(value: Option<T>, what: &str) -> Result<T> {
    value.ok_or_else(|| miette!("Cuebot returned no {what}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[tokio::test]
    async fn connect_fails_with_every_host_listed() {
        // Bind and drop a listener to get a port nothing is listening on.
        let port = std::net::TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port();
        let config = Config {
            timeout: Duration::from_secs(2),
            ..Config::default()
        };
        let hosts = vec![format!("127.0.0.1:{port}")];
        let err = Cuebot::connect(&hosts, &config).await.err().unwrap();
        assert!(err.to_string().contains(&hosts[0]), "{err}");
    }

    #[test]
    fn rpc_errors_name_the_action() {
        let err = rpc_error("finding show 'x'")(Status::not_found("show x does not exist"));
        assert_eq!(
            err.to_string(),
            "finding show 'x' failed: show x does not exist"
        );
        let err = rpc_error("listing hosts")(Status::unavailable(""));
        assert!(err.to_string().starts_with("listing hosts failed: "));
    }
}
