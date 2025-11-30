# OpenCue Kafka-Elasticsearch Indexer

A Rust service that consumes OpenCue monitoring events from Kafka and indexes them into Elasticsearch for historical analysis.

## Overview

This service is the consumer side of the OpenCue monitoring pipeline:

```
Cuebot (Producer) -> Kafka -> kafka-es-indexer (Consumer) -> Elasticsearch
```

## Features

- Consumes events from all OpenCue Kafka topics:
  - `opencue.job.events`
  - `opencue.layer.events`
  - `opencue.frame.events`
  - `opencue.host.events`
  - `opencue.proc.events`
- Bulk indexing to Elasticsearch for efficiency
- Automatic index template creation with proper mappings
- Configurable via CLI arguments, environment variables, or config file
- Graceful shutdown with final flush

## Usage

### Command Line

```bash
kafka-es-indexer \
  --kafka-servers localhost:9092 \
  --kafka-group-id opencue-elasticsearch-indexer \
  --elasticsearch-url http://localhost:9200 \
  --index-prefix opencue \
  --log-level info
```

### Environment Variables

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_GROUP_ID=opencue-elasticsearch-indexer
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_INDEX_PREFIX=opencue
export LOG_LEVEL=info

kafka-es-indexer
```

### Configuration File

```yaml
# config.yaml
kafka:
  bootstrap_servers: "localhost:9092"
  group_id: "opencue-elasticsearch-indexer"
  auto_offset_reset: "earliest"
  enable_auto_commit: true
  auto_commit_interval_ms: 5000

elasticsearch:
  url: "http://localhost:9200"
  index_prefix: "opencue"
  num_shards: 1
  num_replicas: 0
  bulk_size: 100
  flush_interval_ms: 5000
```

```bash
kafka-es-indexer --config config.yaml
```

## Docker

Build the Docker image:

```bash
cd rust
docker build -f crates/kafka-es-indexer/Dockerfile -t opencue/kafka-es-indexer .
```

Run with Docker:

```bash
docker run -d \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e ELASTICSEARCH_URL=http://elasticsearch:9200 \
  opencue/kafka-es-indexer
```

## Building

```bash
cd rust
cargo build --release --package kafka-es-indexer
```

The binary will be at `target/release/kafka-es-indexer`.

## Index Structure

Events are indexed into daily indices with the pattern:

```
{prefix}-{event-type}-{date}
```

Examples:
- `opencue-job-events-2024.11.29`
- `opencue-frame-events-2024.11.29`
