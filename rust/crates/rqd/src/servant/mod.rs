/// Implement Rqd modules for rqd.proto's interfaces
use crate::{config::Config, frame::manager::FrameManager};

use opencue_proto::rqd::{
    rqd_interface_server::RqdInterfaceServer, running_frame_server::RunningFrameServer,
};
use pnet::ipnetwork::IpNetwork;
use rqd_servant::{MachineImpl, RqdServant};
use running_frame_servant::RunningFrameServant;
use std::{
    net::{IpAddr, Ipv4Addr, SocketAddr},
    sync::Arc,
};
use tonic::transport::Server;

pub mod rqd_servant;
pub mod running_frame_servant;

pub type Result<T> = core::result::Result<T, tonic::Status>;

/// Determines the IPv4 address to bind to based on the provided interface name.
fn get_ip_for_interface(rqd_interface: Option<String>) -> Result<Ipv4Addr> {
    match rqd_interface {
        None => Ok(Ipv4Addr::new(0, 0, 0, 0)),
        Some(rqd_interface) => {
            let interface = pnet::datalink::interfaces()
                .into_iter()
                .find(|interface| interface.name == rqd_interface)
                .ok_or_else(|| {
                    tonic::Status::unavailable(format!(
                        "Could not find network interface '{}'",
                        rqd_interface
                    ))
                })?;
            // Find V4 interface
            interface
                .ips
                .iter()
                .find_map(|address| match address {
                    IpNetwork::V4(a) => Some(a.ip()),
                    IpNetwork::V6(_) => None,
                })
                .ok_or_else(|| {
                    tonic::Status::unavailable(format!(
                        "Could not find ipv4 network ip for '{}'",
                        rqd_interface
                    ))
                })
        }
    }
}

pub async fn serve(
    config: Config,
    machine: Arc<MachineImpl>,
    frame_manager: Arc<FrameManager>,
) -> Result<()> {
    let ip_address = get_ip_for_interface(config.grpc.rqd_interface)?;

    let address: SocketAddr = SocketAddr::new(IpAddr::V4(ip_address), config.grpc.rqd_port);

    let running_frame_servant = RunningFrameServant::init(Arc::clone(&frame_manager));
    let rqd_servant = RqdServant::init(machine, Arc::clone(&frame_manager));

    Server::builder()
        .add_service(RunningFrameServer::new(running_frame_servant))
        .add_service(RqdInterfaceServer::new(rqd_servant))
        .serve(address)
        .await
        .map_err(|err| tonic::Status::from_error(Box::new(err)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::Ipv4Addr;

    #[test]
    fn get_ip_for_interface_none_should_return_default() {
        // Arrange: No interface name is provided.
        let interface_name = None;

        // Act: Call the function.
        let result = get_ip_for_interface(interface_name);

        // Assert: The result should be Ok and contain the default "any" address.
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), Ipv4Addr::new(0, 0, 0, 0));
    }

    #[test]
    fn get_ip_for_interface_non_existent_should_error() {
        // Arrange: A non-existent interface name is provided.
        let interface_name = Some("this-interface-does-not-exist".to_string());

        // Act: Call the function.
        let result = get_ip_for_interface(interface_name);

        // Assert: The result should be an "Unavailable" error.
        assert!(result.is_err());
        let status = result.err().unwrap();
        assert_eq!(status.code(), tonic::Code::Unavailable);
        assert!(status
            .message()
            .contains("Could not find network interface"));
    }

    #[test]
    fn get_ip_for_interface_loopback_should_return_localhost_ip() {
        // Arrange: Find the system's loopback interface to make the test environment-agnostic.
        let loopback_interface = pnet::datalink::interfaces()
            .into_iter()
            .find(|iface| iface.is_loopback());

        if let Some(iface) = loopback_interface {
            // Act: Call the function with the found loopback interface name.
            let result = get_ip_for_interface(Some(iface.name));

            // Assert: The result should be Ok and contain the loopback IP (127.0.0.1).
            let ip = result.unwrap_or_else(|e| {
                panic!(
                    "Expected to find an IPv4 for loopback interface, but got an error: {}",
                    e
                )
            });
            assert_eq!(ip, Ipv4Addr::new(127, 0, 0, 1));
        } else {
            // If no loopback interface is found, we skip the test with a message.
            println!("Skipping loopback test: no loopback interface found.");
        }
    }
}
