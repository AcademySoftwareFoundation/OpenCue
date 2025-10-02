use actix::{Message, MessageResponse};
use miette::Result;

use crate::{
    models::{DispatchLayer, Host},
    pipeline::dispatcher::error::DispatchError,
};

/// Message to dispatch a layer to a specific host
#[derive(Message)]
#[rtype(result = "Result<DispatchResult, DispatchError>")]
pub struct DispatchLayerMessage {
    pub layer: DispatchLayer,
    pub host: Host,
}

/// Result of a successful dispatch operation
#[derive(MessageResponse, Debug)]
pub struct DispatchResult {
    pub updated_host: Host,
    pub updated_layer: DispatchLayer,
    #[allow(dead_code)]
    pub dispatched_frames: Vec<String>,
}
