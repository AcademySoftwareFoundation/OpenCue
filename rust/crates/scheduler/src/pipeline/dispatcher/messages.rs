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

use actix::{Message, MessageResponse};
use miette::Result;

use crate::{
    models::{DispatchLayer, Host},
    pipeline::dispatcher::error::DispatchError,
};

/// Actor message to dispatch a layer's frames to a specific host.
///
/// Sends a layer with its frames to the RqdDispatcherService actor for execution
/// on the specified host. The dispatcher will:
/// - Lock the host to prevent concurrent dispatches
/// - Book frames one by one until host resources are exhausted
/// - Update frame states in the database
/// - Communicate with RQD via gRPC to launch frames
/// - Return the updated host and layer state
///
/// # Fields
///
/// * `layer` - Layer containing frames to dispatch
/// * `host` - Target host with available resources
///
/// # Returns
///
/// * `Ok(DispatchResult)` - Successfully dispatched frames with updated state
/// * `Err(DispatchError)` - Dispatch failed due to various errors
#[derive(Message)]
#[rtype(result = "Result<DispatchResult, DispatchError>")]
pub struct DispatchLayerMessage {
    pub layer: DispatchLayer,
    pub host: Host,
}

/// Response returned after a successful dispatch operation.
///
/// Contains the updated state of both the host and layer after dispatching
/// frames. The host reflects consumed resources, and the layer has dispatched
/// frames removed from its frame list.
///
/// # Fields
///
/// * `updated_host` - Host with updated idle resource counts after dispatch
/// * `updated_layer` - Layer with dispatched frames removed from the frames list
/// * `dispatched_frames` - List of frame names that were successfully dispatched
#[derive(MessageResponse, Debug)]
pub struct DispatchResult {
    pub updated_host: Host,
    pub updated_layer: DispatchLayer,
}
