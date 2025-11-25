---
title: "Monitoring system development"
nav_order: 45
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

The monitoring system is implemented in Cuebot and consists of:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cuebot                                  │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────────┐  │
│  │   Service   │───>│ MonitoringManager│───>│ KafkaPublisher │──┬──> Kafka
│  │   Layer     │    └──────────────────┘    └────────────────┘  │
│  └─────────────┘              │              ┌────────────────┐ │
│                               │              │  ESClient      │─┼──> Elasticsearch
│  ┌─────────────┐              │              └────────────────┘ │
│  │ Prometheus  │<─────────────┤              ┌────────────────┐ │
│  │  Metrics    │              └─────────────>│ KafkaConsumer  │─┘
│  └─────────────┘                             └────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Key classes

| Class | Location | Purpose |
|-------|----------|---------|
| `MonitoringManager` | `com.imageworks.spcue.monitoring` | Coordinates event publishing |
| `KafkaEventPublisher` | `com.imageworks.spcue.monitoring` | Publishes events to Kafka |
| `KafkaEventConsumer` | `com.imageworks.spcue.monitoring` | Consumes events for ES indexing |
| `ElasticsearchClient` | `com.imageworks.spcue.monitoring` | Indexes events in Elasticsearch |
| `MonitoringEventBuilder` | `com.imageworks.spcue.monitoring` | Builds event payloads |
| `PrometheusMetrics` | `com.imageworks.spcue.servant` | Exposes Prometheus metrics |

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

Call the monitoring manager from the service layer:

```java
// JobManagerService.java
public void setJobPriority(JobInterface job, int priority) {
    int oldPriority = jobDao.getJobPriority(job);
    jobDao.updatePriority(job, priority);

    // Publish monitoring event
    if (monitoringManager != null) {
        JobDetail detail = jobDao.getJobDetail(job.getJobId());
        monitoringManager.publishEvent(
            MonitoringEventBuilder.buildJobPriorityChangedEvent(
                detail, oldPriority, priority));
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

### Index templates

Create custom index templates for new event types:

```json
{
  "index_patterns": ["opencue-job-admin-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "eventType": { "type": "keyword" },
      "timestamp": { "type": "date" },
      "jobId": { "type": "keyword" },
      "jobName": { "type": "keyword" },
      "showName": { "type": "keyword" },
      "oldPriority": { "type": "integer" },
      "newPriority": { "type": "integer" },
      "user": { "type": "keyword" }
    }
  }
}
```

### Custom indexing logic

Extend `ElasticsearchClient` to add custom indexing:

```java
// ElasticsearchClient.java
public void indexJobAdminEvent(MonitoringEvent event) {
    String indexName = "opencue-job-admin-" +
        LocalDate.now().format(DateTimeFormatter.ISO_DATE);

    Map<String, Object> document = new HashMap<>();
    document.put("eventType", event.getEventType().name());
    document.put("timestamp", event.getTimestamp());
    document.put("jobId", event.getJobId());
    document.put("jobName", event.getJobName());
    document.putAll(event.getMetadataMap());

    indexDocument(indexName, document);
}
```

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

### Elasticsearch configuration

| Property | Default | Description |
|----------|---------|-------------|
| `monitoring.elasticsearch.enabled` | `false` | Enable ES storage |
| `monitoring.elasticsearch.host` | `localhost` | ES host |
| `monitoring.elasticsearch.port` | `9200` | ES port |
| `monitoring.elasticsearch.scheme` | `http` | Connection scheme |
| `monitoring.elasticsearch.index.prefix` | `opencue` | Index name prefix |

### Prometheus configuration

| Property | Default | Description |
|----------|---------|-------------|
| `metrics.prometheus.collector` | `false` | Enable Prometheus metrics |
| `metrics.prometheus.endpoint` | `/metrics` | Metrics endpoint path |

## Debugging

### Enable debug logging

Add to `log4j2.xml`:

```xml
<Logger name="com.imageworks.spcue.monitoring" level="DEBUG"/>
```

### Check event queue status

Monitor the event queue via metrics:

```promql
cue_monitoring_event_queue_size
cue_monitoring_events_dropped_total
```

### Verify Kafka connectivity

```bash
# Check if events are being published
kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic opencue.job.events --from-beginning

# Check consumer group lag
kafka-consumer-groups --bootstrap-server kafka:9092 \
  --group opencue-elasticsearch-indexer --describe
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
