use core::fmt;

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::{
    cluster::Cluster,
    models::{Partitionable, fmt_uuid},
};

/// Basic information to collect a job on the database for dispatching
#[derive(Serialize, Deserialize, Clone)]
pub struct DispatchJob {
    pub id: String,
    pub int_priority: i32,
    pub source_cluster: Cluster,
}

impl fmt::Display for DispatchJob {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", fmt_uuid(&self.id))
    }
}

impl Partitionable for DispatchJob {
    fn partition_key(&self) -> String {
        self.id.to_string()
    }
}
