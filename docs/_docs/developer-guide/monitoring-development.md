---
title: "Monitoring system development"
nav_order: 97
parent: Developer Guide
layout: default
linkTitle: "Monitoring development"
date: 2024-11-24
description: >
  Extend and customize the OpenCue monitoring system
---

# Monitoring system development

### Extend and customize the OpenCue monitoring system

---

This guide explains how to extend, customize, and develop against the OpenCue monitoring system.

## Architecture overview

The monitoring system uses a decoupled architecture with Cuebot publishing events to Kafka and a standalone Rust-based indexer consuming events for Elasticsearch storage:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                Cuebot                                      │
│                                                                            │
│  ┌─────────────┐     ┌─────────────────────┐                               │
│  │   Service   │────>│ KafkaEventPublisher │──────────> Kafka              │
│  │   Layer     │     └─────────────────────┘               │               │
│  └─────────────┘              │                            │               │
│        │                      v                            │               │
│        └─────────────>┌──────────────┐                     │               │
│                       │  Prometheus  │                     │               │
│                       │   Metrics    │                     │               │
│                       └──────────────┘                     │               │
└────────────────────────────────────────────────────────────│───────────────┘
                                                             │
                                                             v
┌────────────────────────────────────────────────────────────────────────────┐
│                      monitoring-indexer (Rust)                             │
│                                                                            │
│  ┌───────────────────┐         ┌─────────────────────────┐                 │
│  │   Kafka Consumer  │────────>│   Elasticsearch Client  │                 │
│  │     (rdkafka)     │         │     (bulk indexing)     │                 │
│  └───────────────────┘         └─────────────────────────┘                 │
│                                            │                               │
└────────────────────────────────────────────│───────────────────────────────┘
                                             v
                                       Elasticsearch
```

**Data flow:**
1. **Service Layer** (e.g., FrameCompleteHandler, HostReportHandler) generates events and calls KafkaEventPublisher
2. **KafkaEventPublisher** serializes events as JSON and publishes them to Kafka topics
3. **monitoring-indexer** (standalone Rust service) consumes events from Kafka topics
4. **monitoring-indexer** bulk indexes events into Elasticsearch for historical storage
5. **Prometheus Metrics** are updated directly by the Service Layer and KafkaEventPublisher (for queue metrics)

### Key components

| Component | Location | Purpose |
|-----------|----------|---------|
| `KafkaEventPublisher` | `com.imageworks.spcue.monitoring` | Publishes events to Kafka |
| `MonitoringEventBuilder` | `com.imageworks.spcue.monitoring` | Builds event payloads |
| `PrometheusMetricsCollector` | `com.imageworks.spcue` | Exposes Prometheus metrics |
| `monitoring-indexer` | `rust/crates/monitoring-indexer/` | Consumes Kafka, indexes to Elasticsearch |

### Why a separate indexer?

The Kafka-to-Elasticsearch indexer is implemented as a standalone Rust service rather than within Cuebot for several reasons:

- **Decoupling**: Cuebot focuses on core scheduling; indexing is a separate concern
- **Scalability**: The indexer can be scaled independently from Cuebot
- **Reliability**: Kafka buffering ensures events are not lost if Elasticsearch is temporarily unavailable
- **Performance**: Rust provides efficient resource usage for high-throughput event processing
- **Operational flexibility**: The indexer can be updated, restarted, or replayed without affecting Cuebot

## Adding new event types

### Step 1: Define the event type

Add the new event type to the `MonitoringEventType` enum:

```java
// MonitoringEventType.java
public enum MonitoringEventType {
    // Existing types...
    JOB_CREATED,
    JOB_STARTED,
    JOB_FINISHED,

    // Add new type
    JOB_PRIORITY_CHANGED
}
```

### Step 2: Create the event builder method

Add a builder method in `MonitoringEventBuilder`:

```java
// MonitoringEventBuilder.java
public static MonitoringEvent buildJobPriorityChangedEvent(
        JobDetail job, int oldPriority, int newPriority) {

    MonitoringEvent.Builder builder = MonitoringEvent.newBuilder()
        .setEventType(MonitoringEventType.JOB_PRIORITY_CHANGED)
        .setTimestamp(Instant.now().toString())
        .setJobId(job.id)
        .setJobName(job.name)
        .setShowName(job.showName);

    // Add custom fields
    builder.putMetadata("oldPriority", String.valueOf(oldPriority));
    builder.putMetadata("newPriority", String.valueOf(newPriority));

    return builder.build();
}
```

### Step 3: Publish the event

Call the Kafka publisher from the service layer:

```java
// JobManagerService.java
@Autowired
private KafkaEventPublisher kafkaEventPublisher;

@Autowired
private MonitoringEventBuilder monitoringEventBuilder;

public void setJobPriority(JobInterface job, int priority) {
    int oldPriority = jobDao.getJobPriority(job);
    jobDao.updatePriority(job, priority);

    // Publish monitoring event
    try {
        JobDetail detail = jobDao.getJobDetail(job.getJobId());
        JobEvent event = monitoringEventBuilder.buildJobPriorityChangedEvent(
            detail, oldPriority, priority);
        kafkaEventPublisher.publishJobEvent(event);
    } catch (Exception e) {
        logger.trace("Failed to publish job priority event: {}", e.getMessage());
    }
}
```

### Step 4: Add Kafka topic (if needed)

If the event requires a new topic, add it to `KafkaEventPublisher`:

```java
// KafkaEventPublisher.java
private static final String TOPIC_JOB_EVENTS = "opencue.job.events";
private static final String TOPIC_JOB_ADMIN_EVENTS = "opencue.job.admin.events"; // New topic

private String getTopicForEvent(MonitoringEventType type) {
    switch (type) {
        case JOB_PRIORITY_CHANGED:
            return TOPIC_JOB_ADMIN_EVENTS;
        // ... existing mappings
        default:
            return TOPIC_JOB_EVENTS;
    }
}
```

## Adding new Prometheus metrics

### Counter metrics

```java
// PrometheusMetrics.java
private static final Counter jobPriorityChanges = Counter.build()
    .name("cue_job_priority_changes_total")
    .help("Total number of job priority changes")
    .labelNames("show", "direction")
    .register();

public static void incrementJobPriorityChange(String show, boolean increased) {
    String direction = increased ? "increased" : "decreased";
    jobPriorityChanges.labels(show, direction).inc();
}
```

### Histogram metrics

```java
private static final Histogram frameQueueTime = Histogram.build()
    .name("cue_frame_queue_time_seconds")
    .help("Time frames spend waiting in queue")
    .labelNames("show")
    .buckets(1, 5, 15, 30, 60, 300, 900, 1800, 3600)
    .register();

public static void observeFrameQueueTime(String show, double seconds) {
    frameQueueTime.labels(show).observe(seconds);
}
```

### Gauge metrics

```java
private static final Gauge activeJobs = Gauge.build()
    .name("cue_active_jobs")
    .help("Number of currently active jobs")
    .labelNames("show", "state")
    .register();

public static void setActiveJobs(String show, String state, int count) {
    activeJobs.labels(show, state).set(count);
}
```

## Customizing Elasticsearch indexing

The `monitoring-indexer` service handles all Elasticsearch indexing. It automatically routes events to indices based on the Kafka topic name.

### Index templates

Create custom index templates for new event types. Note that events use snake_case field names and include a `header` object:

```json
{
  "index_patterns": ["opencue-job-admin-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "header": {
        "properties": {
          "event_id": { "type": "keyword" },
          "event_type": { "type": "keyword" },
          "timestamp": { "type": "date", "format": "epoch_millis" },
          "source_cuebot": { "type": "keyword" },
          "correlation_id": { "type": "keyword" }
        }
      },
      "job_id": { "type": "keyword" },
      "job_name": { "type": "keyword" },
      "show": { "type": "keyword" },
      "old_priority": { "type": "integer" },
      "new_priority": { "type": "integer" },
      "user": { "type": "keyword" }
    }
  }
}
```

### Index naming convention

The monitoring-indexer creates daily indices using the pattern:

```
{topic-name-converted}-YYYY-MM-DD
```

For example:
- `opencue.job.events` → `opencue-job-events-2024-11-29`
- `opencue.frame.events` → `opencue-frame-events-2024-11-29`

## Testing

### Unit testing event builders

```java
@Test
public void testBuildJobPriorityChangedEvent() {
    JobDetail job = createTestJob();

    MonitoringEvent event = MonitoringEventBuilder
        .buildJobPriorityChangedEvent(job, 50, 100);

    assertEquals(MonitoringEventType.JOB_PRIORITY_CHANGED,
                 event.getEventType());
    assertEquals("50", event.getMetadataMap().get("oldPriority"));
    assertEquals("100", event.getMetadataMap().get("newPriority"));
}
```

### Integration testing with embedded Kafka

```java
@EmbeddedKafka(partitions = 1, topics = {"opencue.job.events"})
public class KafkaEventPublisherIntegrationTest {

    @Autowired
    private EmbeddedKafkaBroker embeddedKafka;

    @Autowired
    private KafkaEventPublisher publisher;

    @Test
    public void testPublishEvent() {
        MonitoringEvent event = createTestEvent();
        publisher.publishEvent(event);

        // Verify event was published
        ConsumerRecord<String, String> record =
            KafkaTestUtils.getSingleRecord(consumer, "opencue.job.events");
        assertNotNull(record);
    }
}
```

## Configuration reference

### Kafka configuration

| Property | Default | Description |
|----------|---------|-------------|
| `monitoring.kafka.enabled` | `false` | Enable Kafka publishing |
| `monitoring.kafka.bootstrap.servers` | `localhost:9092` | Kafka broker addresses |
| `monitoring.kafka.queue.capacity` | `1000` | Event queue size |
| `monitoring.kafka.batch.size` | `100` | Batch size for publishing |
| `monitoring.kafka.linger.ms` | `100` | Time to wait before sending batch |
| `monitoring.kafka.acks` | `1` | Required acknowledgments |

### monitoring-indexer configuration

The monitoring-indexer is configured via command-line arguments, environment variables, or a YAML config file:

| CLI Argument | Env Variable | Default | Description |
|--------------|--------------|---------|-------------|
| `--kafka-servers` | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `--kafka-group-id` | `KAFKA_GROUP_ID` | `opencue-monitoring-indexer` | Consumer group ID |
| `--elasticsearch-url` | `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL |
| `--elasticsearch-username` | `ELASTICSEARCH_USERNAME` | - | Elasticsearch username (optional) |
| `--elasticsearch-password` | `ELASTICSEARCH_PASSWORD` | - | Elasticsearch password (optional) |
| `--index-prefix` | `ELASTICSEARCH_INDEX_PREFIX` | `opencue` | Elasticsearch index prefix |
| `--log-level` | `LOG_LEVEL` | `info` | Log level (debug, info, warn, error) |
| `--config` | - | - | Path to YAML config file |

The indexer automatically subscribes to all OpenCue Kafka topics:
- `opencue.job.events`
- `opencue.layer.events`
- `opencue.frame.events`
- `opencue.host.events`
- `opencue.proc.events`

Example with CLI arguments:

```bash
monitoring-indexer \
  --kafka-servers kafka:9092 \
  --kafka-group-id opencue-monitoring-indexer \
  --elasticsearch-url http://elasticsearch:9200 \
  --index-prefix opencue \
  --log-level info
```

Example with environment variables:

```bash
export KAFKA_BOOTSTRAP_SERVERS=kafka:9092
export KAFKA_GROUP_ID=opencue-monitoring-indexer
export ELASTICSEARCH_URL=http://elasticsearch:9200
export ELASTICSEARCH_INDEX_PREFIX=opencue
monitoring-indexer
```

Example with a config file:

```bash
monitoring-indexer --config /path/to/monitoring-indexer.yaml
```

A sample configuration file with complete documentation of all options is available at `rust/config/monitoring-indexer.yaml`.

### Prometheus configuration

| Property | Default | Description |
|----------|---------|-------------|
| `metrics.prometheus.collector` | `false` | Enable Prometheus metrics |
| `metrics.prometheus.endpoint` | `/metrics` | Metrics endpoint path |

## Debugging

### Enable debug logging in Cuebot

Add to `log4j2.xml`:

```xml
<Logger name="com.imageworks.spcue.monitoring" level="DEBUG"/>
```

### Verify Kafka connectivity

```bash
# Check if events are being published
kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic opencue.job.events --from-beginning

# Check consumer group lag
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group opencue-monitoring-indexer --describe
```

### Debugging monitoring-indexer

```bash
# View indexer logs
docker logs opencue-monitoring-indexer

# Check indexer help
docker exec opencue-monitoring-indexer monitoring-indexer --help

# Verify Elasticsearch indices are being created
curl -s "http://localhost:9200/_cat/indices/opencue-*?v"

# Check event counts in Elasticsearch
curl -s "http://localhost:9200/opencue-job-events-*/_count"
curl -s "http://localhost:9200/opencue-frame-events-*/_count"
```

## Best practices

### Event design

- Keep events immutable and self-contained
- Include all relevant context in the event payload
- Use consistent naming conventions for event types
- Version event schemas for backward compatibility

### Performance

- Use bounded queues to prevent memory exhaustion
- Batch events when possible for better throughput
- Monitor queue sizes and dropped events
- Consider event sampling for high-frequency events

### Reliability

- Handle Kafka unavailability gracefully
- Implement retry logic with exponential backoff
- Log dropped events for debugging
- Use idempotent consumers for Elasticsearch indexing

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Contributing to OpenCue](/docs/developer-guide/contributing/) - Submit your changes
