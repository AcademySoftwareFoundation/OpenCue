# OpenCue Monitoring Indexer

A Rust service that consumes OpenCue monitoring events from Kafka and indexes them into Elasticsearch for historical analysis.

## Overview

This service is the consumer side of the OpenCue monitoring pipeline:

```
Cuebot (Producer) -> Kafka -> monitoring-indexer (Consumer) -> Elasticsearch
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
monitoring-indexer \
  --kafka-servers localhost:9092 \
  --kafka-group-id opencue-monitoring-indexer \
  --elasticsearch-url http://localhost:9200 \
  --index-prefix opencue \
  --log-level info
```

### Environment Variables

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_GROUP_ID=opencue-monitoring-indexer
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_INDEX_PREFIX=opencue
export LOG_LEVEL=info

monitoring-indexer
```

### Configuration File

A sample configuration file with complete documentation is available at `rust/config/monitoring-indexer.yaml`.

```bash
monitoring-indexer --config /path/to/monitoring-indexer.yaml
```

See the [sample config](../../config/monitoring-indexer.yaml) for all available options and their descriptions.

## Docker

Build the Docker image:

```bash
cd rust
docker build -f Dockerfile.monitoring-indexer -t opencue/monitoring-indexer .
```

Run with Docker:

```bash
docker run -d \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e ELASTICSEARCH_URL=http://elasticsearch:9200 \
  opencue/monitoring-indexer
```

## Building

```bash
cd rust
cargo build --release --package monitoring-indexer
```

The binary will be at `target/release/monitoring-indexer`.

## Index Structure

Events are indexed into daily indices with the pattern:

```
{prefix}-{event-type}-{date}
```

Examples:
- `opencue-job-events-2024.11.29`
- `opencue-frame-events-2024.11.29`
