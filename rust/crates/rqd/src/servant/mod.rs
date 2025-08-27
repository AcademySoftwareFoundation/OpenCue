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
use tracing::warn;

pub mod rqd_servant;
pub mod running_frame_servant;

pub type Result<T> = core::result::Result<T, tonic::Status>;

pub async fn serve(
    config: Config,
    machine: Arc<MachineImpl>,
    frame_manager: Arc<FrameManager>,
) -> Result<()> {
    let rqd_interface: String = config.grpc.rqd_interface.clone();
    let mut ip_address: Ipv4Addr = Ipv4Addr::new(0, 0, 0, 0);
    if !rqd_interface.is_empty() {
        if let Some(interface) = pnet::datalink::interfaces()
            .into_iter()
            .find(|interface| interface.name == rqd_interface)
        {
            if let Some(IpNetwork::V4(ipv4_network)) = interface.ips.iter().find(|ip| ip.is_ipv4()) {
                ip_address = ipv4_network.ip();
            } else {
                warn!(
                    "Could not find an IPv4 address for interface '{}'. Binding to 0.0.0.0",
                    rqd_interface
                );
            }
        } else {
            warn!(
                "Could not find network interface '{}'. Binding to 0.0.0.0",
                rqd_interface
            );
        }
    }
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
