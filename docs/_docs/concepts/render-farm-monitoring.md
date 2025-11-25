---
title: "Render farm monitoring"
nav_order: 25
parent: Concepts
layout: default
linkTitle: "Render farm monitoring"
date: 2024-11-24
description: >
  Understanding the OpenCue render farm monitoring system
---

# Render farm monitoring

### Understanding the OpenCue render farm monitoring system

---

OpenCue provides a comprehensive monitoring system for tracking render farm operations, collecting metrics, and analyzing historical data. This system enables real-time visibility into job execution, resource utilization, and system health.

## Overview

The monitoring system is built on an event-driven architecture that captures lifecycle events from jobs, layers, frames, hosts, and processes. These events can be:

- **Published to Kafka** for real-time streaming and integration with external systems
- **Stored in Elasticsearch** for historical analysis and querying
- **Exposed as Prometheus metrics** for real-time dashboards and alerting

## Architecture

The monitoring system consists of three main components:

### Event publishing (Kafka)

Cuebot publishes events to Apache Kafka topics when significant state changes occur:

| Topic | Description |
|-------|-------------|
| `opencue.job.events` | Job lifecycle events (created, started, finished, killed) |
| `opencue.layer.events` | Layer state changes |
| `opencue.frame.events` | Frame execution events (started, completed, failed, retried) |
| `opencue.host.events` | Host state changes (up, down, locked, nimby) |
| `opencue.host.reports` | Periodic host status reports with resource utilization |
| `opencue.proc.events` | Process allocation and deallocation events |

Events are published asynchronously to avoid impacting render farm performance. A bounded queue ensures the system remains responsive even under high load.

### Historical storage (Elasticsearch)

The Kafka event consumer indexes events into Elasticsearch for long-term storage and analysis. This enables:

- **Historical queries**: Search for jobs, frames, or hosts by any attribute
- **Trend analysis**: Track metrics over time (job completion rates, failure patterns)
- **Capacity planning**: Analyze resource utilization patterns
- **Debugging**: Investigate issues by examining historical event sequences

Elasticsearch indices are organized by event type and time-based partitioning for efficient querying.

### Metrics collection (Prometheus)

Cuebot exposes a `/metrics` endpoint compatible with Prometheus. Key metrics include:

**Job and frame metrics:**
- `cue_frames_completed_total` - Counter of completed frames by state
- `cue_jobs_completed_total` - Counter of completed jobs by show
- `cue_frame_runtime_seconds` - Histogram of frame execution times
- `cue_frame_memory_bytes` - Histogram of frame memory usage

**Queue metrics:**
- `cue_dispatch_waiting_total` - Tasks waiting in dispatch queue
- `cue_booking_waiting_total` - Tasks waiting in booking queue
- `cue_report_executed_total` - Host reports processed

**Monitoring system metrics:**
- `cue_monitoring_events_published_total` - Events published to Kafka
- `cue_monitoring_events_dropped_total` - Events dropped due to queue overflow
- `cue_monitoring_event_queue_size` - Current event queue size

## Event types

### Job events

Job events capture the complete lifecycle of rendering jobs:

- **JOB_CREATED**: A new job was submitted to the queue
- **JOB_STARTED**: The job began executing (first frame dispatched)
- **JOB_FINISHED**: All frames completed successfully
- **JOB_KILLED**: The job was manually terminated
- **JOB_PAUSED**: The job was paused
- **JOB_RESUMED**: The job was resumed from paused state

### Frame events

Frame events track individual frame execution:

- **FRAME_STARTED**: A frame began rendering on a host
- **FRAME_COMPLETED**: A frame finished successfully
- **FRAME_FAILED**: A frame failed with an error
- **FRAME_RETRIED**: A failed frame was retried
- **FRAME_EATEN**: A frame was marked as complete without rendering

### Host events

Host events monitor render node status:

- **HOST_UP**: A host came online
- **HOST_DOWN**: A host went offline
- **HOST_LOCKED**: A host was locked for maintenance
- **HOST_UNLOCKED**: A host was unlocked
- **HOST_NIMBY_LOCKED**: A host entered NIMBY mode
- **HOST_NIMBY_UNLOCKED**: A host exited NIMBY mode

## Configuration

The monitoring system is configured through Cuebot properties:

```properties
# Kafka event publishing
monitoring.kafka.enabled=true
monitoring.kafka.bootstrap.servers=kafka:9092

# Elasticsearch storage
monitoring.elasticsearch.enabled=true
monitoring.elasticsearch.host=elasticsearch
monitoring.elasticsearch.port=9200

# Prometheus metrics
metrics.prometheus.collector=true
```

Each component can be enabled or disabled independently based on your infrastructure needs.

## What's next?

- [Quick start: Setting up monitoring](/docs/quick-starts/quick-start-monitoring/) - Deploy the monitoring stack
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Monitoring developer guide](/docs/developer-guide/monitoring-development/) - Extend and customize the monitoring system
