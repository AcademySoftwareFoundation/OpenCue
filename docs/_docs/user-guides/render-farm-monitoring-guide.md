---
title: "Render farm monitoring guide"
nav_order: 43
parent: User Guides
layout: default
linkTitle: "Render farm monitoring"
date: 2024-11-24
description: >
  Configure and use the OpenCue render farm monitoring system
---

# Render farm monitoring guide

### Configure and use the OpenCue render farm monitoring system

---

This guide explains how to use the OpenCue monitoring system to track render farm operations, create custom dashboards, and set up alerts.

## Overview

The OpenCue monitoring system provides three ways to observe your render farm:

1. **Real-time metrics** via Prometheus and Grafana
2. **Event streaming** via Kafka
3. **Historical analysis** via Elasticsearch and Kibana

## Configuring Cuebot for monitoring

### Enabling Kafka event publishing

Add these properties to your Cuebot configuration:

```properties
# Enable Kafka event publishing
monitoring.kafka.enabled=true
monitoring.kafka.bootstrap.servers=your-kafka-host:9092

# Optional: Configure event queue
monitoring.kafka.queue.capacity=1000
monitoring.kafka.batch.size=100
```

Or pass them as command-line arguments:

```bash
java -jar cuebot.jar \
  --monitoring.kafka.enabled=true \
  --monitoring.kafka.bootstrap.servers=kafka:9092
```

### Enabling Elasticsearch storage

```properties
# Enable Elasticsearch historical storage
monitoring.elasticsearch.enabled=true
monitoring.elasticsearch.host=your-elasticsearch-host
monitoring.elasticsearch.port=9200
```

### Enabling Prometheus metrics

```properties
# Enable Prometheus metrics endpoint
metrics.prometheus.collector=true
```

The metrics endpoint is available at `http://cuebot-host:8080/metrics`.

## Using Grafana dashboards

### Accessing the dashboard

1. Open Grafana at your configured URL (default: `http://localhost:3000`)
2. Navigate to **Dashboards** > **OpenCue Monitoring Dashboard**

### Dashboard panels

The pre-configured dashboard includes:

#### Frame metrics

| Panel | Description | Metric |
|-------|-------------|--------|
| Frame Completion Rate | Frames completed per 5 minutes by state | `rate(cue_frames_completed_total[5m])` |
| Frame Runtime Distribution | P50 and P95 frame execution times | `histogram_quantile(0.95, cue_frame_runtime_seconds_bucket)` |
| Frame Memory Usage | Memory consumption distribution | `histogram_quantile(0.95, cue_frame_memory_bytes_bucket)` |

#### Job metrics

| Panel | Description | Metric |
|-------|-------------|--------|
| Job Completion Rate | Jobs completed per show | `rate(cue_jobs_completed_total[5m])` |

#### System health

| Panel | Description | Metric |
|-------|-------------|--------|
| Event Queue Size | Pending events in publish queue | `cue_monitoring_event_queue_size` |
| Events Published | Events successfully sent to Kafka | `rate(cue_monitoring_events_published_total[5m])` |
| Events Dropped | Events lost due to queue overflow | `rate(cue_monitoring_events_dropped_total[5m])` |
| Host Reports | Reports received from render hosts | `rate(cue_host_reports_received_total[5m])` |

### Creating custom panels

To create a custom panel:

1. Click **Add** > **Visualization**
2. Select **Prometheus** as the data source
3. Enter your PromQL query
4. Configure visualization options

Example queries:

```promql
# Average frame runtime by show (last hour)
avg(rate(cue_frame_runtime_seconds_sum[1h])) by (show)
  / avg(rate(cue_frame_runtime_seconds_count[1h])) by (show)

# Failed frame rate
rate(cue_frames_completed_total{state="DEAD"}[5m])

# Queue saturation
cue_dispatch_waiting_total / cue_dispatch_remaining_capacity_total
```

### Setting up alerts

To create an alert in Grafana:

1. Edit a panel or create a new one
2. Click the **Alert** tab
3. Configure alert conditions

Example alert: High event drop rate

```yaml
Alert name: High Event Drop Rate
Condition: rate(cue_monitoring_events_dropped_total[5m]) > 10
For: 5m
Message: "Monitoring events are being dropped. Check Kafka connectivity."
```

Example alert: Cuebot down

```yaml
Alert name: Cuebot Down
Condition: up{job="cuebot"} == 0
For: 1m
Message: "Cuebot is not responding to Prometheus scrapes."
```

## Using Kafka for event streaming

### Viewing events

Use the Kafka console consumer to view events:

```bash
# View job events
kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic opencue.job.events --from-beginning

# View frame events (latest only)
kafka-console-consumer --bootstrap-server kafka:9092 \
  --topic opencue.frame.events
```

### Event format

Events are published as JSON messages:

```json
{
  "eventType": "FRAME_COMPLETED",
  "timestamp": "2024-11-24T10:30:00Z",
  "source": "cuebot-01",
  "payload": {
    "jobId": "job-uuid",
    "jobName": "show-shot-user_render",
    "layerId": "layer-uuid",
    "layerName": "render",
    "frameId": "frame-uuid",
    "frameName": "0001-render",
    "frameNumber": 1,
    "exitStatus": 0,
    "runtime": 3600,
    "maxRss": 8589934592,
    "host": "render-node-01"
  }
}
```

### Integrating with external systems

Kafka events can be consumed by external systems for:

- **Custom alerting**: Build alerts based on specific job or frame conditions
- **Cost tracking**: Calculate render costs based on resource usage
- **Capacity planning**: Analyze usage patterns for infrastructure planning
- **Reporting**: Generate custom reports on render farm utilization

Example Python consumer:

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'opencue.frame.events',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    event = message.value
    if event['eventType'] == 'FRAME_FAILED':
        print(f"Frame failed: {event['payload']['frameName']}")
        # Send alert, update database, etc.
```

## Using Elasticsearch for historical analysis

### Querying events in Kibana

1. Open Kibana at your configured URL (default: `http://localhost:5601`)
2. Navigate to **Discover**
3. Select the `opencue-*` index pattern
4. Use KQL to search events

Example queries:

```
# Find all failed frames for a job
eventType: "FRAME_FAILED" AND payload.jobName: "myshow*"

# Find jobs that took longer than 1 hour
eventType: "JOB_FINISHED" AND payload.runtime > 3600

# Find host down events
eventType: "HOST_DOWN" AND payload.host: "render-*"
```

### Creating visualizations

In Kibana, you can create:

- **Time series**: Frame completion over time
- **Pie charts**: Frame states distribution
- **Data tables**: Top failing jobs or layers
- **Metrics**: Average frame runtime

### Retention and cleanup

Configure Elasticsearch index lifecycle management (ILM) to manage data retention:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "7d",
            "max_size": "50gb"
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

## Prometheus metrics reference

### Job metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_jobs_completed_total` | Counter | show | Total jobs completed |
| `cue_frames_completed_total` | Counter | state, show | Total frames completed |
| `cue_frame_runtime_seconds` | Histogram | show | Frame execution time |
| `cue_frame_memory_bytes` | Histogram | show | Frame memory usage |

### Queue metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_dispatch_waiting_total` | Gauge | - | Dispatch queue size |
| `cue_dispatch_threads_total` | Gauge | - | Active dispatch threads |
| `cue_booking_waiting_total` | Gauge | - | Booking queue size |
| `cue_report_executed_total` | Gauge | - | Host reports processed |

### Monitoring system metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cue_monitoring_events_published_total` | Counter | event_type | Events published to Kafka |
| `cue_monitoring_events_dropped_total` | Counter | event_type | Events dropped |
| `cue_monitoring_event_queue_size` | Gauge | - | Current queue size |
| `cue_host_reports_received_total` | Counter | facility | Host reports received |

## Best practices

### Dashboard organization

- Create separate dashboards for operations, capacity planning, and debugging
- Use template variables to filter by show, facility, or time range
- Set appropriate refresh intervals (5s for real-time, 1m for overview)

### Alert tuning

- Start with conservative thresholds and adjust based on baseline
- Use `for` clauses to avoid alerting on transient spikes
- Include runbook links in alert messages

### Data retention

- Keep high-resolution metrics for 2-4 weeks
- Downsample older data for long-term trends
- Archive raw events to cold storage if needed for compliance

## What's next?

- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend and customize the monitoring system
- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
