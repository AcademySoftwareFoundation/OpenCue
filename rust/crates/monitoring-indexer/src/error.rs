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

//! Error types for the Kafka-Elasticsearch indexer.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum IndexerError {
    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Kafka error: {0}")]
    Kafka(String),

    #[error("Elasticsearch error: {0}")]
    Elasticsearch(String),

    #[error("JSON parsing error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

impl From<rdkafka::error::KafkaError> for IndexerError {
    fn from(err: rdkafka::error::KafkaError) -> Self {
        IndexerError::Kafka(err.to_string())
    }
}

impl From<elasticsearch::Error> for IndexerError {
    fn from(err: elasticsearch::Error) -> Self {
        IndexerError::Elasticsearch(err.to_string())
    }
}
