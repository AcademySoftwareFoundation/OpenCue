---
title: "Monitoring tutorial"
nav_order: 84
parent: Tutorials
layout: default
linkTitle: "Monitoring tutorial"
date: 2024-11-24
description: >
  Build custom monitoring dashboards and alerts for your OpenCue render farm
---

# Monitoring tutorial

### Build custom monitoring dashboards and alerts for your OpenCue render farm

---

This tutorial walks you through setting up monitoring for your OpenCue render farm, creating custom Grafana dashboards, and configuring alerts.

## Prerequisites

- OpenCue sandbox environment running (see [Using the OpenCue Sandbox for Testing](/docs/developer-guide/sandbox-testing/))
- Monitoring stack deployed (see [Quick start for monitoring](/docs/quick-starts/quick-start-monitoring/))
- Basic familiarity with Prometheus and Grafana

## Monitoring stack components

| Component | Purpose | URL | Port |
|-----------|---------|-----|------|
| **Grafana** | Dashboards and visualization | [http://localhost:3000](http://localhost:3000) | 3000 |
| **Prometheus** | Metrics collection | [http://localhost:9090](http://localhost:9090) | 9090 |
| **Kafka UI** | Event stream browser | [http://localhost:8090](http://localhost:8090) | 8090 |
| **Kibana** | Elasticsearch visualization | [http://localhost:5601](http://localhost:5601) | 5601 |
| **Elasticsearch** | Historical data storage | [http://localhost:9200](http://localhost:9200) | 9200 |
| **Kafka** | Event streaming | localhost:9092 | 9092 |
| **kafka-es-indexer** | Kafka to Elasticsearch indexer | - | - |
| **Zookeeper** | Kafka coordination | localhost:2181 | 2181 |

### Grafana: OpenCue Monitoring Grafana Dashboard

![OpenCue Monitoring Grafana Dashboard](/assets/images/opencue_monitoring/opencue_monitoring_grafana_chart.png)

### Prometheus Metrics Interface

![Prometheus Metrics Interface](/assets/images/opencue_monitoring/opencue_monitoring_prometheus.png)

### UI for Apache Kafka

![UI for Apache Kafka](/assets/images/opencue_monitoring/opencue_monitoring_ui_for_apache_kafka.png)

### Elasticsearch Kibana - Dev Tools

![Kibana](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch_kibana_dev_tools.png)

### Elasticsearch

![Elasticsearch](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch.png)

## Tutorial goals

By the end of this tutorial, you will:

1. Create a custom Grafana dashboard for job monitoring
2. Build a Prometheus alert for failed frames
3. Set up a Kafka consumer to process events
4. Query historical data in Elasticsearch

## Part 1: Creating a custom Grafana dashboard

### Step 1: Access Grafana

1. Open Grafana at [http://localhost:3000](http://localhost:3000)
2. Log in with username `admin` and password `admin`
3. Click **Dashboards** in the left menu

### Step 2: Create a new dashboard

1. Click **New** > **New Dashboard**
2. Click **Add visualization**
3. Select **Prometheus** as the data source

### Step 3: Add a frame completion panel

Create a time series panel showing frame completions:

1. In the Query tab, enter:
   ```promql
   sum(increase(cue_frames_completed_total[5m])) by (state)
   ```

2. Configure the panel:
   - Title: "Frames Completed by State (5m)"
   - Legend: `{{state}}`
   - Unit: `short`

3. Click **Apply**

### Step 4: Add a job queue panel

Add a gauge showing pending work:

1. Click **Add** > **Visualization**
2. Select **Prometheus** as the data source
3. Enter the query:
   ```promql
   cue_dispatch_waiting_total
   ```

4. Change visualization to **Gauge**
5. Configure:
   - Title: "Dispatch Queue Size"
   - Thresholds: 0 (green), 100 (yellow), 500 (red)

6. Click **Apply**

### Step 5: Add a host report panel

Create a panel showing host activity:

1. Click **Add** > **Visualization**
2. Enter the query:
   ```promql
   sum(increase(cue_host_reports_received_total[5m])) by (facility)
   ```

3. Configure:
   - Title: "Host Reports by Facility"
   - Visualization: Time series

4. Click **Apply**

### Step 6: Save the dashboard

1. Click the save icon (or Ctrl+S)
2. Name: "My OpenCue Dashboard"
3. Click **Save**

## Part 2: Creating Prometheus alerts

### Step 1: Create an alert rule

1. In Grafana, go to **Alerting** > **Alert rules**
2. Click **New alert rule**

### Step 2: Configure the alert condition

1. Name: "High Frame Failure Rate"
2. In Query section:
   ```promql
   rate(cue_frames_completed_total{state="DEAD"}[5m]) > 0.1
   ```

3. Set condition:
   - Threshold: IS ABOVE 0.1
   - For: 5m

### Step 3: Add alert details

1. Add summary:
   ```
   Frame failure rate is {{ $value }} per second
   ```

2. Add description:
   ```
   The render farm is experiencing elevated frame failures.
   Check host health and job configurations.
   ```

3. Click **Save and exit**

### Step 4: Create a notification contact point

1. Go to **Alerting** > **Contact points**
2. Click **Add contact point**
3. Configure for your notification method (email, Slack, etc.)

## Part 3: Building a Kafka event consumer

### Step 1: Create a Python consumer

Create a file `monitor_events.py`:

```python
#!/usr/bin/env python3
"""
Simple Kafka consumer for OpenCue monitoring events.
"""

from kafka import KafkaConsumer
import json
from datetime import datetime

# Connect to Kafka
# Note: The cuebot producer uses lz4 compression, so the lz4 library must be installed
consumer = KafkaConsumer(
    'opencue.frame.events',
    'opencue.job.events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    group_id='tutorial-consumer'
)

print("Listening for OpenCue events...")
print("-" * 60)

for message in consumer:
    event = message.value

    # Events have a 'header' field containing event metadata
    header = event.get('header', {})
    event_type = header.get('event_type', 'UNKNOWN')
    timestamp = header.get('timestamp', '')

    # Convert timestamp from milliseconds to readable format
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp) / 1000)
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            pass

    # Format output based on event type
    if event_type.startswith('FRAME_'):
        job_name = event.get('job_name', 'N/A')
        frame_name = event.get('frame_name', 'N/A')
        state = event.get('state', 'N/A')
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {job_name}")
        print(f"  Frame: {frame_name}")
        print(f"  State: {state}")
        if event_type == 'FRAME_COMPLETED':
            runtime = event.get('run_time', 0)
            print(f"  Runtime: {runtime}s")
        elif event_type == 'FRAME_FAILED':
            exit_status = event.get('exit_status', -1)
            print(f"  Exit Status: {exit_status}")
        print()

    elif event_type.startswith('JOB_'):
        job_name = event.get('job_name', 'N/A')
        show_name = event.get('show', 'N/A')
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {job_name}")
        print(f"  Show: {show_name}")
        print()
```

### Step 2: Install dependencies

```bash
pip install kafka-python lz4
```

### Step 3: Run the consumer

```bash
python monitor_events.py
```

### Step 4: Generate events

In another terminal, submit a test job. You can use either cuecmd or PyOutline:

**Option A: Using cuecmd**

```bash
# Create a command file
echo "echo Hello from monitoring test" > /tmp/test_commands.txt

# Submit the job
cuecmd /tmp/test_commands.txt --show testing --job-name monitoring_test
```

**Option B: Using PyOutline**

```bash
python -c "
import outline
from outline.modules.shell import Shell

ol = outline.Outline('monitoring_test_$RANDOM', shot='testshot', show='testing')
layer = Shell('test_layer', command=['/bin/echo', 'Hello from monitoring test'], range='1-1')
ol.add_layer(layer)
outline.cuerun.launch(ol, use_pycuerun=False)
"
```

Watch the consumer output as events flow through Kafka.

## Part 4: Querying Elasticsearch

![Kibana Dashboard](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch_kibana_dashboard1.png)

### Step 1: Access Kibana

1. Open Kibana at [http://localhost:5601](http://localhost:5601)
2. Navigate to **Management** > **Stack Management** > **Index Patterns**

### Step 2: Create an index pattern

1. Click **Create index pattern**
2. Enter pattern: `opencue-*`
3. Select `header.timestamp` as the time field (format: epoch_millis)
4. Click **Create index pattern**

### Step 3: Explore events

1. Navigate to **Discover**
2. Select the `opencue-*` index pattern
3. Set the time range to include your test events

### Step 4: Run KQL queries

![Kibana Dev Tools](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch_kibana_dev_tools.png)

Try these example queries:

```
# Find all failed frames
header.event_type: "FRAME_FAILED"

# Find events for a specific job
job_name: "test*"

# Find frames that took longer than 1 hour
header.event_type: "FRAME_COMPLETED" AND run_time > 3600

# Find host down events
header.event_type: "HOST_DOWN"
```

### Step 5: Create a visualization

1. Navigate to **Visualize Library**
2. Click **Create visualization**
3. Select **Lens**
4. Drag `eventType` to the visualization
5. Create a pie chart of event types

## Part 5: Building a failure tracking dashboard

Let's create a comprehensive failure tracking dashboard.

### Step 1: Create failure rate panel

In Grafana, create a new panel:

```promql
sum(rate(cue_frames_completed_total{state="DEAD"}[1h])) by (show)
/ sum(rate(cue_frames_completed_total[1h])) by (show)
* 100
```

Configure:
- Title: "Frame Failure Rate by Show (%)"
- Unit: `percent (0-100)`

### Step 2: Create retry tracking panel

```promql
sum(increase(cue_frames_completed_total{state="DEAD"}[24h])) by (show)
```

Configure:
- Title: "Failed Frames (24h)"
- Visualization: Bar gauge

### Step 3: Create host health panel

```promql
sum(up{job="cuebot"})
```

Configure:
- Title: "Cuebot Health"
- Visualization: Stat
- Color mode: Background
- Thresholds: 0 (red), 1 (green)

### Step 4: Organize the dashboard

1. Arrange panels in a logical layout
2. Add row headers: "Farm Health", "Job Metrics", "Failures"
3. Set dashboard refresh rate to 30s
4. Save the dashboard

## Challenge exercises

### Exercise 1: Memory usage alert

Create an alert that fires when average frame memory exceeds 16GB:

```promql
histogram_quantile(0.95, sum(rate(cue_frame_memory_bytes_bucket[5m])) by (le))
> 17179869184
```

### Exercise 2: Capacity planning query

Build a Grafana panel showing peak usage times:

```promql
max_over_time(cue_dispatch_threads_total[1d])
```

### Exercise 3: Custom Kafka processor

Extend the Python consumer to:
- Track frame failure rates per show
- Send Slack notifications for high failure rates
- Write metrics to a time-series database

## Cleanup

To stop the monitoring stack:

```bash
docker compose -f sandbox/docker-compose.monitoring-full.yml down
```

To preserve your Grafana dashboards, export them first:
1. Open the dashboard
2. Click the share icon
3. Select **Export** > **Save to file**

## What's next?

- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Advanced configuration
- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend the system
- [Monitoring reference](/docs/reference/monitoring-reference/) - Complete API reference
