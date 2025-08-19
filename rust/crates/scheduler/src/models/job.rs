use core::fmt;

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{Partitionable, fmt_uuid};

/// Basic information to collect a job on the database for dispatching
#[derive(Serialize, Deserialize, Clone)]
pub struct DispatchJob {
    #[serde(
        serialize_with = "serialize_uuid",
        deserialize_with = "deserialize_uuid"
    )]
    pub id: Uuid,
    pub int_priority: i32,
    pub age_days: i32,
}

fn serialize_uuid<S>(uuid: &Uuid, serializer: S) -> Result<S::Ok, S::Error>
where
    S: serde::Serializer,
{
    serializer.serialize_str(&uuid.to_string())
}

fn deserialize_uuid<'de, D>(deserializer: D) -> Result<Uuid, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let s = String::deserialize(deserializer)?;
    Uuid::parse_str(&s).map_err(serde::de::Error::custom)
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
