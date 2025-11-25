---
title: "Monitoring system reference"
nav_order: 70
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

## Kafka topics

### Topic specifications

| Topic | Partition Key | Description |
|-------|---------------|-------------|
| `opencue.job.events` | `jobId` | Job lifecycle events |
| `opencue.layer.events` | `layerId` | Layer state changes |
| `opencue.frame.events` | `frameId` | Frame execution events |
| `opencue.host.events` | `hostId` | Host state changes |
| `opencue.host.reports` | `hostId` | Periodic host status reports |
| `opencue.proc.events` | `procId` | Process allocation events |

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

### Job event payload

```json
{
  "eventType": "JOB_FINISHED",
  "timestamp": "2024-11-24T10:30:00.000Z",
  "source": "cuebot-01",
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "jobName": "show-shot-user_render_v001",
  "showName": "show",
  "showId": "550e8400-e29b-41d4-a716-446655440001",
  "facilityName": "cloud",
  "groupName": "render",
  "userName": "artist",
  "state": "FINISHED",
  "isPaused": false,
  "isAutoEat": false,
  "startTime": "2024-11-24T09:00:00.000Z",
  "stopTime": "2024-11-24T10:30:00.000Z",
  "frameCount": 100,
  "layerCount": 2,
  "pendingFrames": 0,
  "runningFrames": 0,
  "deadFrames": 0,
  "succeededFrames": 100
}
```

### Frame event payload

```json
{
  "eventType": "FRAME_COMPLETED",
  "timestamp": "2024-11-24T10:30:00.000Z",
  "source": "cuebot-01",
  "frameId": "550e8400-e29b-41d4-a716-446655440002",
  "frameName": "0001-render",
  "frameNumber": 1,
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "jobName": "show-shot-user_render_v001",
  "layerId": "550e8400-e29b-41d4-a716-446655440003",
  "layerName": "render",
  "showName": "show",
  "state": "SUCCEEDED",
  "exitStatus": 0,
  "retryCount": 0,
  "runtime": 3600,
  "llTime": 3500,
  "maxRss": 8589934592,
  "usedGpuMemory": 0,
  "host": "render-node-01",
  "coresUsed": 8,
  "gpusUsed": 0
}
```

### Host report payload

```json
{
  "eventType": "HOST_REPORT",
  "timestamp": "2024-11-24T10:30:00.000Z",
  "source": "cuebot-01",
  "hostId": "550e8400-e29b-41d4-a716-446655440004",
  "hostName": "render-node-01",
  "facilityName": "cloud",
  "allocName": "render.general",
  "state": "UP",
  "lockState": "OPEN",
  "nimbyEnabled": false,
  "totalCores": 64,
  "idleCores": 32,
  "totalMemory": 137438953472,
  "freeMemory": 68719476736,
  "totalGpuMemory": 25769803776,
  "freeGpuMemory": 25769803776,
  "load": 1250,
  "pingTime": 1732443000000,
  "bootTime": 1732300000000,
  "os": "Linux",
  "runningProcs": 4
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

### Monitoring system metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_monitoring_events_published_total` | Counter | `event_type` | Events published to Kafka |
| `cue_monitoring_events_dropped_total` | Counter | `event_type` | Events dropped due to queue overflow |
| `cue_monitoring_event_queue_size` | Gauge | - | Current event queue size |
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

### Elasticsearch configuration

```properties
# Enable/disable Elasticsearch storage
monitoring.elasticsearch.enabled=false

# Connection settings
monitoring.elasticsearch.host=localhost
monitoring.elasticsearch.port=9200
monitoring.elasticsearch.scheme=http

# Authentication (optional)
monitoring.elasticsearch.username=
monitoring.elasticsearch.password=

# Index settings
monitoring.elasticsearch.index.prefix=opencue
monitoring.elasticsearch.index.shards=1
monitoring.elasticsearch.index.replicas=0

# Bulk indexing
monitoring.elasticsearch.bulk.size=100
monitoring.elasticsearch.bulk.flush.interval=5000
```

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
- `opencue-host-reports-2024.11.24`

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
| `ES_JAVA_OPTS` | elasticsearch | JVM options |
| `GF_SECURITY_ADMIN_USER` | grafana | Admin username |
| `GF_SECURITY_ADMIN_PASSWORD` | grafana | Admin password |

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend the monitoring system
