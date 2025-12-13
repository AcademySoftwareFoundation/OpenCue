---
title: "Monitoring system reference"
nav_order: 72
parent: Reference
layout: default
linkTitle: "Monitoring reference"
date: 2024-11-24
description: >
  Complete reference for the OpenCue monitoring system
---

# Monitoring system reference

### Complete reference for the OpenCue monitoring system

---

This reference provides comprehensive documentation for all monitoring system components, configuration options, and APIs.

## Component access

| Component | Purpose | URL | Port |
|-----------|---------|-----|------|
| **Grafana** | Dashboards and visualization | [http://localhost:3000](http://localhost:3000) | 3000 |
| **Prometheus** | Metrics collection and querying | [http://localhost:9090](http://localhost:9090) | 9090 |
| **Kafka UI** | Event stream browser | [http://localhost:8090](http://localhost:8090) | 8090 |
| **Kibana** | Elasticsearch visualization | [http://localhost:5601](http://localhost:5601) | 5601 |
| **Elasticsearch** | Historical data storage | [http://localhost:9200](http://localhost:9200) | 9200 |
| **Kafka** | Event streaming broker | localhost:9092 | 9092 |
| **Zookeeper** | Kafka coordination | localhost:2181 | 2181 |
| **Cuebot Metrics** | Prometheus metrics endpoint | [http://localhost:8080/metrics](http://localhost:8080/metrics) | 8080 |

### Prometheus Metrics Interface

![Prometheus Metrics Interface](/assets/images/opencue_monitoring/opencue_monitoring_prometheus.png)

### OpenCue Monitoring Grafana Dashboard

![OpenCue Monitoring Grafana Dashboard](/assets/images/opencue_monitoring/opencue_monitoring_grafana_chart.png)


## Kafka topics

### Topic specifications

| Topic | Partition Key | Description |
|-------|---------------|-------------|
| `opencue.job.events` | `jobId` | Job lifecycle events |
| `opencue.layer.events` | `layerId` | Layer state changes |
| `opencue.frame.events` | `frameId` | Frame execution events |
| `opencue.host.events` | `hostId` | Host state changes |
| `opencue.proc.events` | `procId` | Process allocation events |

![Kafka UI for Apache Kafka](/assets/images/opencue_monitoring/opencue_monitoring_ui_for_apache_kafka.png)

### Event types

#### Job events

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `JOB_CREATED` | Job submitted to queue | Job submission |
| `JOB_STARTED` | First frame dispatched | Frame dispatch |
| `JOB_FINISHED` | All frames complete | Last frame completion |
| `JOB_KILLED` | Job manually terminated | User action |
| `JOB_PAUSED` | Job paused | User action |
| `JOB_RESUMED` | Job resumed | User action |

#### Layer events

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `LAYER_STARTED` | First frame of layer dispatched | Frame dispatch |
| `LAYER_FINISHED` | All frames in layer complete | Last frame completion |

#### Frame events

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `FRAME_STARTED` | Frame began rendering | RQD reports start |
| `FRAME_COMPLETED` | Frame finished successfully | RQD reports completion |
| `FRAME_FAILED` | Frame failed with error | RQD reports failure |
| `FRAME_RETRIED` | Failed frame requeued | Automatic retry |
| `FRAME_EATEN` | Frame marked complete without rendering | User action |

#### Host events

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `HOST_UP` | Host came online | RQD registration |
| `HOST_DOWN` | Host went offline | Heartbeat timeout |
| `HOST_LOCKED` | Host locked for maintenance | User action |
| `HOST_UNLOCKED` | Host unlocked | User action |
| `HOST_NIMBY_LOCKED` | Host entered NIMBY mode | NIMBY activation |
| `HOST_NIMBY_UNLOCKED` | Host exited NIMBY mode | NIMBY deactivation |

#### Proc events

| Event Type | Description | Trigger |
|------------|-------------|---------|
| `PROC_ASSIGNED` | Process allocated to frame | Dispatch |
| `PROC_UNASSIGNED` | Process deallocated | Frame completion/failure |

## Event payload schemas

All events include a `header` field with common metadata, plus event-specific fields at the top level.

### Event header

```json
{
  "header": {
    "event_id": "f533d84a-1586-4980-8c5e-3443376425c9",
    "event_type": "FRAME_COMPLETED",
    "timestamp": "1764097486229",
    "source_cuebot": "cuebot-01",
    "correlation_id": "fa7bbb9a-cae1-4f6b-a50a-88a9ac349d24"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique identifier for this event |
| `event_type` | string | Type of event (e.g., FRAME_COMPLETED, JOB_FINISHED) |
| `timestamp` | string | Unix timestamp in milliseconds |
| `source_cuebot` | string | Hostname of the Cuebot that generated the event |
| `correlation_id` | string | ID linking related events (typically the job ID) |

### Job event payload

```json
{
  "header": {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "JOB_FINISHED",
    "timestamp": "1732446600000",
    "source_cuebot": "cuebot-01",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_name": "show-shot-user_render_v001",
  "show": "show",
  "show_id": "550e8400-e29b-41d4-a716-446655440001",
  "facility": "cloud",
  "group_name": "render",
  "user": "artist",
  "state": "FINISHED",
  "is_paused": false,
  "is_auto_eat": false,
  "start_time": "1732443000000",
  "stop_time": "1732446600000",
  "frame_count": 100,
  "layer_count": 2,
  "pending_frames": 0,
  "running_frames": 0,
  "dead_frames": 0,
  "succeeded_frames": 100
}
```

### Frame event payload

```json
{
  "header": {
    "event_id": "f533d84a-1586-4980-8c5e-3443376425c9",
    "event_type": "FRAME_COMPLETED",
    "timestamp": "1764097486229",
    "source_cuebot": "cuebot-01",
    "correlation_id": "fa7bbb9a-cae1-4f6b-a50a-88a9ac349d24"
  },
  "frame_id": "fa18c460-0e92-49e1-8d6a-e26473ac2708",
  "frame_name": "0001-render",
  "frame_number": 1,
  "layer_id": "53ec9034-b16b-4cc2-9eec-05f68b1848bf",
  "layer_name": "render",
  "job_id": "fa7bbb9a-cae1-4f6b-a50a-88a9ac349d24",
  "job_name": "show-shot-user_render_v001",
  "show": "show",
  "state": "SUCCEEDED",
  "previous_state": "RUNNING",
  "exit_status": 0,
  "exit_signal": 0,
  "retry_count": 0,
  "dispatch_order": 0,
  "start_time": "1764097475839",
  "stop_time": "1764097486233",
  "run_time": 3600,
  "llu_time": "1764097476",
  "max_rss": "8589934592",
  "used_memory": "8589934592",
  "reserved_memory": "262144",
  "max_gpu_memory": "0",
  "used_gpu_memory": "0",
  "reserved_gpu_memory": "0",
  "num_cores": 8,
  "num_gpus": 0,
  "host_name": "render-node-01",
  "resource_id": "357516fe-4d34-447f-b1cd-41779102b6e3",
  "checkpoint_state": "DISABLED",
  "checkpoint_count": 0,
  "total_core_time": 0,
  "total_gpu_time": 0,
  "reason": "",
  "killed_by": ""
}
```

## Prometheus metrics

### Job and frame metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_jobs_completed_total` | Counter | `show` | Total jobs completed |
| `cue_frames_completed_total` | Counter | `state`, `show` | Total frames completed |
| `cue_frame_runtime_seconds` | Histogram | `show` | Frame execution time distribution |
| `cue_frame_memory_bytes` | Histogram | `show` | Frame memory usage distribution |
| `cue_frame_kill_failure_counter_total` | Counter | - | Frames that failed to be killed |

### Queue metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_dispatch_waiting_total` | Gauge | - | Tasks waiting in dispatch queue |
| `cue_dispatch_threads_total` | Gauge | - | Active dispatch threads |
| `cue_dispatch_executed_total` | Gauge | - | Dispatch tasks executed |
| `cue_dispatch_rejected_total` | Gauge | - | Dispatch tasks rejected |
| `cue_dispatch_remaining_capacity_total` | Gauge | - | Dispatch queue remaining capacity |
| `cue_booking_waiting_total` | Gauge | - | Tasks waiting in booking queue |
| `cue_booking_threads_total` | Gauge | - | Active booking threads |
| `cue_booking_remaining_capacity_total` | Gauge | - | Booking queue remaining capacity |
| `cue_manage_waiting_total` | Gauge | - | Tasks waiting in manage queue |
| `cue_report_executed_total` | Gauge | - | Host reports processed |
| `cue_report_rejected_total` | Gauge | - | Host reports rejected |

### Host metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_host_reports_received_total` | Counter | `facility` | Host reports received |

### Query metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_find_jobs_by_show_count_total` | Counter | - | FIND_JOBS_BY_SHOW query count |
| `cue_booking_durations_histogram_in_millis` | Histogram | - | Booking step durations |

## Configuration reference

### Kafka configuration

```properties
# Enable/disable Kafka event publishing
monitoring.kafka.enabled=false

# Kafka broker addresses (comma-separated for multiple brokers)
monitoring.kafka.bootstrap.servers=localhost:9092

# Event queue configuration
monitoring.kafka.queue.capacity=1000

# Producer configuration
monitoring.kafka.batch.size=16384
monitoring.kafka.linger.ms=100
monitoring.kafka.buffer.memory=33554432
monitoring.kafka.acks=1
monitoring.kafka.retries=3
monitoring.kafka.retry.backoff.ms=100

# Compression
monitoring.kafka.compression.type=lz4
```

### monitoring-indexer configuration

Elasticsearch indexing is handled by the standalone `monitoring-indexer` service (located at `rust/crates/monitoring-indexer/`). It can be configured via environment variables or CLI arguments:

| CLI Argument | Env Variable | Default | Description |
|--------------|--------------|---------|-------------|
| `--kafka-servers` | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `--kafka-group-id` | `KAFKA_GROUP_ID` | `opencue-monitoring-indexer` | Consumer group ID |
| `--elasticsearch-url` | `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL |
| `--elasticsearch-username` | `ELASTICSEARCH_USERNAME` | - | Elasticsearch username (optional) |
| `--elasticsearch-password` | `ELASTICSEARCH_PASSWORD` | - | Elasticsearch password (optional) |
| `--index-prefix` | `ELASTICSEARCH_INDEX_PREFIX` | `opencue` | Elasticsearch index prefix |
| `--log-level` | `LOG_LEVEL` | `info` | Log level (debug, info, warn, error) |

Example using environment variables:

```bash
export KAFKA_BOOTSTRAP_SERVERS=kafka:9092
export ELASTICSEARCH_URL=http://elasticsearch:9200
export ELASTICSEARCH_INDEX_PREFIX=opencue
monitoring-indexer
```

Example using CLI arguments:

```bash
monitoring-indexer \
  --kafka-servers kafka:9092 \
  --elasticsearch-url http://elasticsearch:9200 \
  --index-prefix opencue
```

Example using a configuration file:

```bash
monitoring-indexer --config /path/to/monitoring-indexer.yaml
```

A sample configuration file with complete documentation of all options is available at `rust/config/monitoring-indexer.yaml`.

### Prometheus configuration

```properties
# Enable/disable Prometheus metrics endpoint
metrics.prometheus.collector=false

# Histogram bucket configuration
metrics.prometheus.frame.runtime.buckets=1,5,10,30,60,300,600,1800,3600,7200
metrics.prometheus.frame.memory.buckets=1073741824,2147483648,4294967296,8589934592,17179869184
```

## Elasticsearch indices

### Index naming convention

```
{prefix}-{event-category}-{date}
```

Examples:
- `opencue-job-events-2024.11.24`
- `opencue-frame-events-2024.11.24`
- `opencue-host-events-2024.11.24`

### Index mappings

#### Job events index

```json
{
  "mappings": {
    "properties": {
      "eventType": { "type": "keyword" },
      "timestamp": { "type": "date" },
      "source": { "type": "keyword" },
      "jobId": { "type": "keyword" },
      "jobName": { "type": "keyword" },
      "showName": { "type": "keyword" },
      "facilityName": { "type": "keyword" },
      "userName": { "type": "keyword" },
      "state": { "type": "keyword" },
      "frameCount": { "type": "integer" },
      "layerCount": { "type": "integer" },
      "runtime": { "type": "long" }
    }
  }
}
```

#### Frame events index

```json
{
  "mappings": {
    "properties": {
      "eventType": { "type": "keyword" },
      "timestamp": { "type": "date" },
      "frameId": { "type": "keyword" },
      "frameName": { "type": "keyword" },
      "jobId": { "type": "keyword" },
      "jobName": { "type": "keyword" },
      "layerName": { "type": "keyword" },
      "showName": { "type": "keyword" },
      "state": { "type": "keyword" },
      "exitStatus": { "type": "integer" },
      "runtime": { "type": "long" },
      "maxRss": { "type": "long" },
      "host": { "type": "keyword" },
      "coresUsed": { "type": "integer" }
    }
  }
}
```

## gRPC monitoring service

### Service definition

```protobuf
service MonitoringInterface {
  // Get current monitoring configuration
  rpc GetMonitoringConfig(MonitoringConfigRequest)
      returns (MonitoringConfigResponse);

  // Get monitoring statistics
  rpc GetMonitoringStats(MonitoringStatsRequest)
      returns (MonitoringStatsResponse);

  // Query historical events
  rpc QueryEvents(QueryEventsRequest)
      returns (QueryEventsResponse);

  // Stream real-time events
  rpc StreamEvents(StreamEventsRequest)
      returns (stream MonitoringEvent);
}
```

### Message definitions

```protobuf
message MonitoringEvent {
  MonitoringEventType event_type = 1;
  string timestamp = 2;
  string source = 3;
  string job_id = 4;
  string job_name = 5;
  string show_name = 6;
  map<string, string> metadata = 7;
}

enum MonitoringEventType {
  JOB_CREATED = 0;
  JOB_STARTED = 1;
  JOB_FINISHED = 2;
  JOB_KILLED = 3;
  JOB_PAUSED = 4;
  JOB_RESUMED = 5;
  FRAME_STARTED = 10;
  FRAME_COMPLETED = 11;
  FRAME_FAILED = 12;
  FRAME_RETRIED = 13;
  HOST_UP = 20;
  HOST_DOWN = 21;
  HOST_LOCKED = 22;
  HOST_UNLOCKED = 23;
}
```

## Docker compose reference

### Full monitoring stack

The `docker-compose.monitoring-full.yml` includes:

| Service | Image | Ports |
|---------|-------|-------|
| zookeeper | confluentinc/cp-zookeeper:7.4.0 | 2181 |
| kafka | confluentinc/cp-kafka:7.4.0 | 9092, 29092 |
| kafka-ui | provectuslabs/kafka-ui:latest | 8090 |
| monitoring-indexer | opencue/monitoring-indexer | - |
| elasticsearch | elasticsearch:8.8.0 | 9200, 9300 |
| kibana | kibana:8.8.0 | 5601 |
| prometheus | prom/prometheus:v2.45.0 | 9090 |
| grafana | grafana/grafana:10.0.0 | 3000 |

### Environment variables

| Variable | Service | Description |
|----------|---------|-------------|
| `KAFKA_BROKER_ID` | kafka | Unique broker identifier |
| `KAFKA_ZOOKEEPER_CONNECT` | kafka | Zookeeper connection string |
| `KAFKA_AUTO_CREATE_TOPICS_ENABLE` | kafka | Enable automatic topic creation |
| `KAFKA_BOOTSTRAP_SERVERS` | monitoring-indexer | Kafka broker addresses |
| `ELASTICSEARCH_URL` | monitoring-indexer | Elasticsearch URL |
| `ELASTICSEARCH_USERNAME` | monitoring-indexer | Elasticsearch username (optional) |
| `ELASTICSEARCH_PASSWORD` | monitoring-indexer | Elasticsearch password (optional) |
| `ELASTICSEARCH_INDEX_PREFIX` | monitoring-indexer | Elasticsearch index prefix |
| `ES_JAVA_OPTS` | elasticsearch | JVM options |
| `GF_SECURITY_ADMIN_USER` | grafana | Admin username |
| `GF_SECURITY_ADMIN_PASSWORD` | grafana | Admin password |

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend the monitoring system
