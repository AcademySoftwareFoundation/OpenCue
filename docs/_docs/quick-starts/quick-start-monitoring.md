---
title: "Quick start for OpenCue monitoring stack"
nav_order: 9
parent: Quick Starts
layout: default
linkTitle: "Quick start for monitoring"
date: 2024-11-24
description: >
  Deploy the OpenCue monitoring stack with Kafka, Elasticsearch, Prometheus, and Grafana
---

# Quick start for OpenCue monitoring stack

### Deploy the OpenCue monitoring stack

---

This guide walks you through deploying the OpenCue monitoring stack, which provides real-time metrics, event streaming, and historical data storage for your render farm.

## Before you begin

Ensure you have the following:

- A working OpenCue sandbox environment (see [Using the OpenCue Sandbox for Testing](/docs/developer-guide/sandbox-testing/))
- Docker and Docker Compose installed
- At least 8GB of available RAM for the monitoring services

## Monitoring stack components

The monitoring stack includes:

| Component | Purpose | Port |
|-----------|---------|------|
| **Kafka** | Event streaming | 9092 |
| **Zookeeper** | Kafka coordination | 2181 |
| **Elasticsearch** | Historical data storage | 9200 |
| **Prometheus** | Metrics collection | 9090 |
| **Grafana** | Dashboards and visualization | 3000 |
| **Kafka UI** | Kafka topic browser | 8090 |
| **Kibana** | Elasticsearch visualization | 5601 |

## Step-by-step setup

### Step 1: Start the monitoring stack

From the OpenCue repository root, start the full monitoring stack:

```bash
docker compose -f sandbox/docker-compose.monitoring-full.yml up -d
```

This command starts all monitoring services along with Cuebot configured to publish events.

Wait for all services to become healthy:

```bash
docker compose -f sandbox/docker-compose.monitoring-full.yml ps
```

All containers should show status `Up` or `healthy`.

### Step 2: Verify Kafka topics

Check that Kafka topics were created:

```bash
docker exec opencue-kafka kafka-topics --bootstrap-server localhost:29092 --list
```

You should see:

```
opencue.frame.events
opencue.host.events
opencue.host.reports
opencue.job.events
opencue.layer.events
opencue.proc.events
```

### Step 3: Access Grafana

1. Open Grafana at [http://localhost:3000](http://localhost:3000)
2. Log in with:
   - Username: `admin`
   - Password: `admin`
3. Navigate to **Dashboards** to find the pre-configured OpenCue monitoring dashboard

![OpenCue Monitoring Grafana Dashboard](/assets/images/opencue_monitoring/opencue_monitoring_grafana_chart.png)

### Step 4: Verify Prometheus metrics

1. Open Prometheus at [http://localhost:9090](http://localhost:9090)
2. Navigate to **Status** > **Targets**
3. Verify that the `cuebot` target shows status `UP`

![Prometheus Metrics Interface](/assets/images/opencue_monitoring/opencue_monitoring_prometheus.png)

You can also query metrics directly:

```bash
curl -s http://localhost:8080/metrics | grep cue_
```

### Step 5: Browse Kafka events

1. Open Kafka UI at [http://localhost:8090](http://localhost:8090)
2. Click on the `opencue` cluster
3. Browse topics to see events as they are published

![Kafka UI for Apache Kafka](/assets/images/opencue_monitoring/opencue_monitoring_ui_for_apache_kafka.png)

## Testing the monitoring system

### Generate test events

Submit a test job to generate monitoring events.

**Option A: Using cuecmd**

```bash
# Create a command file
echo "echo Hello from monitoring test" > /tmp/test_commands.txt

# Submit the job
cuecmd /tmp/test_commands.txt --show testing --job-name monitoring_test
```

**Option B: Using PyOutline**

```bash
# Install pycue if not already installed
pip install ./pycue ./pyoutline

# Submit a test job
python -c "
import outline
from outline.modules.shell import Shell

ol = outline.Outline('monitoring_test_job', shot='testshot', show='testing')
layer = Shell('test_layer', command=['/bin/echo', 'Hello from monitoring test'], range='1-1')
ol.add_layer(layer)
outline.cuerun.launch(ol, use_pycuerun=False)
"
```

### View events in real-time

Watch Kafka events as jobs execute:

```bash
docker exec opencue-kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic opencue.frame.events \
  --from-beginning
```

Or use the Python consumer script (requires lz4 for decompression):

```bash
pip install kafka-python lz4
python sandbox/monitor_events.py
```

### Query Prometheus metrics

Open Prometheus at [http://localhost:9090](http://localhost:9090) and try these queries:

- `cue_monitoring_events_published_total` - Total events published
- `cue_frames_completed_total` - Completed frames by state
- `rate(cue_host_reports_received_total[5m])` - Host report rate

## Grafana dashboard panels

The pre-configured dashboard includes:

- **Frames Completed (5m)**: Real-time frame completion by state (DEAD, SUCCEEDED, WAITING)
- **Jobs Completed by Show (5m)**: Jobs completed per show
- **Frame Runtime Distribution**: P50 and P95 frame execution times
- **Frame Memory Usage Distribution**: Memory consumption distribution
- **Monitoring Event Queue Size**: Event publishing queue depth
- **Events Published (5m)**: Frame Completed, Frame Failed, Frame Retried, Host Boot, Host Report
- **Events Dropped (5m)**: Dropped events (should be 0)
- **Host Reports Received (5m)**: Host reporting activity by facility

## Accessing monitoring components

### Grafana - Dashboards and Visualization

**URL:** [http://localhost:3000](http://localhost:3000)

**Login:** admin / admin

Grafana provides pre-configured dashboards for monitoring your render farm:

1. Navigate to **Dashboards** > **OpenCue Monitoring Dashboard**
2. View real-time metrics for frames, jobs, and hosts
3. Create custom dashboards using Prometheus as the data source

### Prometheus - Metrics Collection

**URL:** [http://localhost:9090](http://localhost:9090)

Prometheus collects and stores time-series metrics from Cuebot:

1. Navigate to **Status** > **Targets** to verify Cuebot is being scraped
2. Use the **Graph** tab to query metrics:
   - `cue_frames_completed_total` - Frames by state
   - `cue_jobs_completed_total` - Jobs by show
   - `cue_monitoring_events_published_total` - Published events
3. Navigate to **Status** > **Configuration** to view scrape settings

### Kafka UI - Event Stream Browser

**URL:** [http://localhost:8090](http://localhost:8090)

Kafka UI allows you to browse event topics and messages:

1. Click on the **opencue** cluster
2. Navigate to **Topics** to see all event topics:
   - `opencue.frame.events` - Frame lifecycle events
   - `opencue.job.events` - Job lifecycle events
   - `opencue.host.events` - Host status events
   - `opencue.host.reports` - Host report events
   - `opencue.proc.events` - Proc allocation events
3. Click on a topic and select **Messages** to view events in real-time

### Elasticsearch - Historical Data Storage

**URL:** [http://localhost:9200](http://localhost:9200)

Elasticsearch stores historical event data for analysis:

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# List indices
curl http://localhost:9200/_cat/indices?v

# Count events
curl http://localhost:9200/opencue-*/_count

# Search for failed frames
curl -X GET "http://localhost:9200/opencue-*/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "header.event_type": "FRAME_FAILED"
    }
  },
  "size": 5
}'
```

### Kibana - Elasticsearch Visualization

**URL:** [http://localhost:5601](http://localhost:5601)

Kibana provides a UI for exploring Elasticsearch data:

1. Navigate to **Management** > **Stack Management** > **Index Patterns**
2. Create an index pattern: `opencue-*`
3. Select `header.timestamp` as the time field (format: epoch_millis)
4. Navigate to **Discover** to explore events
5. Use KQL queries:
   - `header.event_type: "FRAME_FAILED"` - Find failed frames
   - `job_name: "test*"` - Find events for jobs matching pattern
   - `header.event_type: "FRAME_COMPLETED" AND run_time > 3600` - Long-running frames

![Kibana Dashboard](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch_kibana_dashboard1.png)

![Kibana Dev Tools](/assets/images/opencue_monitoring/opencue_monitoring_elasticsearch_kibana_dev_tools.png)

## Stopping the monitoring stack

To stop all monitoring services:

```bash
docker compose -f sandbox/docker-compose.monitoring-full.yml down
```

To stop and remove all data volumes:

```bash
docker compose -f sandbox/docker-compose.monitoring-full.yml down -v
```

## Troubleshooting

### Cuebot fails to start

Check Cuebot logs for errors:

```bash
docker logs opencue-cuebot
```

Common issues:
- Kafka not ready: Ensure Zookeeper and Kafka are healthy before Cuebot starts
- Elasticsearch connection: Verify Elasticsearch is accessible

### No metrics in Prometheus

1. Verify Cuebot exposes metrics: `curl http://localhost:8080/metrics`
2. Check Prometheus targets: Navigate to **Status** > **Targets** in Prometheus
3. Verify the Prometheus configuration file mounts correctly

### Kafka topics not created

Topics are auto-created when Cuebot publishes the first event. If topics are missing:

1. Check Cuebot logs for Kafka connection errors
2. Verify Kafka is healthy: `docker logs opencue-kafka`
3. Ensure `KAFKA_AUTO_CREATE_TOPICS_ENABLE` is set to `true`

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Learn about the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure alerts and custom dashboards
- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend the monitoring system
