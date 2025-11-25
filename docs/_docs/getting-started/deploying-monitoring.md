---
title: "Deploying the monitoring stack"
nav_order: 31
parent: Getting Started
layout: default
linkTitle: "Deploying monitoring"
date: 2024-11-24
description: >
  Deploy the OpenCue render farm monitoring stack for production environments
---

# Deploying the monitoring stack

### Deploy the OpenCue render farm monitoring stack for production environments

---

This guide explains how to deploy the OpenCue monitoring stack components for production use. The monitoring system provides real-time metrics, event streaming, and historical data storage for your render farm.

## Overview

The OpenCue monitoring system consists of three main components:

| Component | Purpose | Required |
|-----------|---------|----------|
| **Kafka** | Event streaming for job, frame, and host events | Optional |
| **Elasticsearch** | Historical event storage and analysis | Optional |
| **Prometheus** | Real-time metrics collection | Optional |

Each component can be enabled independently based on your monitoring requirements.

## System requirements

### Kafka cluster

- **Memory**: Minimum 4GB RAM per broker
- **Storage**: SSD recommended, size depends on retention period
- **Network**: Low-latency connection to Cuebot

### Elasticsearch

- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: SSD recommended, plan for ~1KB per event
- **JVM**: Heap size should be 50% of available RAM (max 32GB)

### Prometheus

- **Memory**: 2GB minimum, scales with number of metrics
- **Storage**: SSD recommended, ~2 bytes per sample

## Before you begin

Ensure you have:

- A working Cuebot deployment (see [Deploying Cuebot](/docs/getting-started/deploying-cuebot/))
- Docker and Docker Compose (for containerized deployment)
- Network connectivity between Cuebot and monitoring services

## Deployment options

### Option 1: Docker Compose (recommended for testing)

Use the provided Docker Compose file for a complete monitoring stack:

```bash
cd /path/to/OpenCue
docker compose -f sandbox/docker-compose.monitoring-full.yml up -d
```

This starts all monitoring services with default configurations suitable for development and testing.

### Option 2: Production deployment

For production environments, deploy each component separately with appropriate configurations.

#### Deploying Kafka

1. Set up a Kafka cluster with Zookeeper (or use KRaft mode for Kafka 3.x+):

   ```bash
   # Example using Docker
   docker run -d --name zookeeper \
     -p 2181:2181 \
     confluentinc/cp-zookeeper:7.4.0

   docker run -d --name kafka \
     -p 9092:9092 \
     -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
     -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 \
     confluentinc/cp-kafka:7.4.0
   ```

2. Create the required topics:

   ```bash
   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.job.events --partitions 3 --replication-factor 1

   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.frame.events --partitions 6 --replication-factor 1

   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.host.events --partitions 3 --replication-factor 1

   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.host.reports --partitions 3 --replication-factor 1

   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.layer.events --partitions 3 --replication-factor 1

   kafka-topics --bootstrap-server kafka:9092 --create \
     --topic opencue.proc.events --partitions 3 --replication-factor 1
   ```

#### Deploying Elasticsearch

1. Deploy Elasticsearch:

   ```bash
   docker run -d --name elasticsearch \
     -p 9200:9200 \
     -e discovery.type=single-node \
     -e xpack.security.enabled=false \
     -e "ES_JAVA_OPTS=-Xms4g -Xmx4g" \
     docker.elastic.co/elasticsearch/elasticsearch:8.8.0
   ```

2. Create index templates for OpenCue events:

   ```bash
   curl -X PUT "localhost:9200/_index_template/opencue-events" \
     -H "Content-Type: application/json" \
     -d '{
       "index_patterns": ["opencue-*"],
       "template": {
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
             "showName": { "type": "keyword" }
           }
         }
       }
     }'
   ```

#### Deploying Prometheus

1. Create a Prometheus configuration file (`prometheus.yml`):

   ```yaml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s

   scrape_configs:
     - job_name: 'cuebot'
       static_configs:
         - targets: ['cuebot-host:8080']
       metrics_path: /metrics
   ```

2. Deploy Prometheus:

   ```bash
   docker run -d --name prometheus \
     -p 9090:9090 \
     -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
     prom/prometheus:v2.45.0
   ```

#### Deploying Grafana (optional)

1. Deploy Grafana for visualization:

   ```bash
   docker run -d --name grafana \
     -p 3000:3000 \
     -e GF_SECURITY_ADMIN_PASSWORD=admin \
     grafana/grafana:10.0.0
   ```

2. Configure Prometheus as a data source in Grafana.

3. Import the OpenCue dashboard from `sandbox/config/grafana/dashboards/opencue-monitoring.json`.

## Configuring Cuebot

Enable monitoring in Cuebot by adding configuration properties.

### Using command-line arguments

```bash
java -jar cuebot.jar \
  --datasource.cue-data-source.jdbc-url=jdbc:postgresql://db-host/cuebot \
  --datasource.cue-data-source.username=cuebot \
  --datasource.cue-data-source.password=<password> \
  --monitoring.kafka.enabled=true \
  --monitoring.kafka.bootstrap.servers=kafka-host:9092 \
  --monitoring.elasticsearch.enabled=true \
  --monitoring.elasticsearch.host=elasticsearch-host \
  --monitoring.elasticsearch.port=9200 \
  --metrics.prometheus.collector=true
```

### Using environment variables

```bash
export MONITORING_KAFKA_ENABLED=true
export MONITORING_KAFKA_BOOTSTRAP_SERVERS=kafka-host:9092
export MONITORING_ELASTICSEARCH_ENABLED=true
export MONITORING_ELASTICSEARCH_HOST=elasticsearch-host
export MONITORING_ELASTICSEARCH_PORT=9200
export METRICS_PROMETHEUS_COLLECTOR=true
```

### Using application properties

Add to `application.properties` or `opencue.properties`:

```properties
# Kafka event publishing
monitoring.kafka.enabled=true
monitoring.kafka.bootstrap.servers=kafka-host:9092

# Elasticsearch storage
monitoring.elasticsearch.enabled=true
monitoring.elasticsearch.host=elasticsearch-host
monitoring.elasticsearch.port=9200

# Prometheus metrics
metrics.prometheus.collector=true
```

## Verifying the deployment

### Check Kafka topics

```bash
kafka-topics --bootstrap-server kafka-host:9092 --list
```

Expected output includes:
```
opencue.frame.events
opencue.host.events
opencue.host.reports
opencue.job.events
opencue.layer.events
opencue.proc.events
```

### Check Prometheus targets

Open Prometheus at `http://prometheus-host:9090/targets` and verify the Cuebot target shows status `UP`.

### Check Cuebot metrics

```bash
curl http://cuebot-host:8080/metrics | grep cue_
```

You should see metrics like:
```
cue_monitoring_events_published_total
cue_frames_completed_total
cue_dispatch_waiting_total
```

### Check Elasticsearch indices

```bash
curl http://elasticsearch-host:9200/_cat/indices/opencue-*
```

## Security considerations

### Kafka security

For production deployments, configure:

- **SSL/TLS encryption** for data in transit
- **SASL authentication** for client authentication
- **ACLs** to restrict topic access

### Elasticsearch security

Enable X-Pack security features:

- **Authentication** for API access
- **TLS** for transport and HTTP layers
- **Role-based access control** for indices

### Prometheus security

- Use **basic authentication** or **OAuth** for the web UI
- Configure **TLS** for scrape endpoints
- Use **network policies** to restrict access

## Troubleshooting

### Cuebot fails to connect to Kafka

1. Verify Kafka is running: `kafka-broker-api-versions --bootstrap-server kafka-host:9092`
2. Check network connectivity from Cuebot to Kafka
3. Verify the bootstrap servers configuration matches your Kafka deployment

### Events not appearing in Elasticsearch

1. Check Cuebot logs for Elasticsearch connection errors
2. Verify Elasticsearch is healthy: `curl http://elasticsearch-host:9200/_cluster/health`
3. Ensure the Kafka consumer is running (check for `KafkaEventConsumer` in logs)

### Prometheus not scraping metrics

1. Verify the metrics endpoint is accessible: `curl http://cuebot-host:8080/metrics`
2. Check Prometheus configuration for correct target address
3. Review Prometheus logs for scrape errors

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Monitoring reference](/docs/reference/monitoring-reference/) - Complete configuration reference
