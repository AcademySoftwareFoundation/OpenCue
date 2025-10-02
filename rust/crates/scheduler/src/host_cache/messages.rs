use actix::{Message, MessageResponse};

use bytesize::ByteSize;
use miette::Result;

use crate::{
    cluster_key::{ClusterKey, Tag},
    host_cache::HostCacheError,
    models::{CoreSize, Host},
};

#[derive(MessageResponse)]
pub struct CheckedOutHost(pub ClusterKey, pub Host);

#[derive(Message)]
#[rtype(result = "Result<CheckedOutHost, HostCacheError>")]
pub struct CheckOut<F>
where
    F: Fn(&Host) -> bool,
{
    pub facility_id: String,
    pub show_id: String,
    pub tags: Vec<Tag>,
    pub cores: CoreSize,
    pub memory: ByteSize,
    pub validation: F,
}

#[derive(Message)]
#[rtype(result = "()")]
pub struct CheckIn(pub ClusterKey, pub Host);

#[derive(Message)]
#[rtype(result =  CacheRatioResponse)]
pub struct CacheRatio;

#[derive(MessageResponse)]
pub struct CacheRatioResponse {
    #[allow(dead_code)]
    pub hit: u64,
    #[allow(dead_code)]
    pub miss: u64,
    pub hit_ratio: usize,
}
