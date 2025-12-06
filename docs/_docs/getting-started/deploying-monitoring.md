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

The OpenCue monitoring system consists of:

| Component | Purpose | Required |
|-----------|---------|----------|
| **Kafka** | Event streaming for job, frame, and host events | Optional |
| **kafka-es-indexer** | Standalone Rust service that indexes Kafka events to Elasticsearch | Optional (required for ES) |
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

#### Deploying kafka-es-indexer

The `kafka-es-indexer` is a standalone Rust service that consumes events from Kafka and indexes them into Elasticsearch. It runs separately from Cuebot.

1. Build the Docker image (from OpenCue repository root):

   ```bash
   cd rust
   docker build -f Dockerfile.kafka-es-indexer -t opencue/kafka-es-indexer .
   ```

2. Run the indexer:

   ```bash
   docker run -d --name kafka-es-indexer \
     --network your-network \
     -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
     -e KAFKA_GROUP_ID=opencue-elasticsearch-indexer \
     -e ELASTICSEARCH_URL=http://elasticsearch:9200 \
     -e ELASTICSEARCH_INDEX_PREFIX=opencue \
     opencue/kafka-es-indexer
   ```

   Or with CLI arguments:

   ```bash
   docker run -d --name kafka-es-indexer \
     --network your-network \
     opencue/kafka-es-indexer \
     --kafka-servers kafka:9092 \
     --kafka-group-id opencue-elasticsearch-indexer \
     --elasticsearch-url http://elasticsearch:9200 \
     --index-prefix opencue
   ```

   Or with a configuration file (mount the config file into the container):

   ```bash
   docker run -d --name kafka-es-indexer \
     --network your-network \
     -v /path/to/kafka-es-indexer.yaml:/etc/opencue/kafka-es-indexer.yaml \
     opencue/kafka-es-indexer \
     --config /etc/opencue/kafka-es-indexer.yaml
   ```

   A sample configuration file with complete documentation is available at `rust/config/kafka-es-indexer.yaml`.

3. Verify the indexer is running:

   ```bash
   docker logs kafka-es-indexer
   ```

   You should see log messages indicating successful connection to Kafka and Elasticsearch.

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

Enable monitoring in Cuebot by adding configuration properties. Note that Elasticsearch indexing is handled by the standalone `kafka-es-indexer` service, not Cuebot.

### Using command-line arguments

```bash
java -jar cuebot.jar \
  --datasource.cue-data-source.jdbc-url=jdbc:postgresql://db-host/cuebot \
  --datasource.cue-data-source.username=cuebot \
  --datasource.cue-data-source.password=<password> \
  --monitoring.kafka.enabled=true \
  --monitoring.kafka.bootstrap.servers=kafka-host:9092 \
  --metrics.prometheus.collector=true
```

### Using environment variables

```bash
export MONITORING_KAFKA_ENABLED=true
export MONITORING_KAFKA_BOOTSTRAP_SERVERS=kafka-host:9092
export METRICS_PROMETHEUS_COLLECTOR=true
```

### Using application properties

Add to `application.properties` or `opencue.properties`:

```properties
# Kafka event publishing
monitoring.kafka.enabled=true
monitoring.kafka.bootstrap.servers=kafka-host:9092

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
opencue.job.events
opencue.layer.events
opencue.proc.events
```

### Check Prometheus targets

Open Prometheus at `http://prometheus-host:9090/targets` and verify the Cuebot target shows status `UP`.

### Check Cuebot metrics

```bash
curl -s http://localhost:8080/metrics | grep -E "^cue_"
```

**Note:** Replace localhost with the Cuebot hostname or IP.

You should see metrics like:
```
cue_frames_completed_total
cue_dispatch_waiting_total
cue_host_reports_received_total
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

1. Check kafka-es-indexer logs: `docker logs kafka-es-indexer`
2. Verify Elasticsearch is healthy: `curl http://elasticsearch-host:9200/_cluster/health`
3. Verify kafka-es-indexer is connected to Kafka and consuming messages
4. Check that indices are being created: `curl http://elasticsearch-host:9200/_cat/indices/opencue-*`

### Prometheus not scraping metrics

1. Verify the metrics endpoint is accessible: `curl http://cuebot-host:8080/metrics`
2. Check Prometheus configuration for correct target address
3. Review Prometheus logs for scrape errors

## What's next?

- [Render farm monitoring concepts](/docs/concepts/render-farm-monitoring/) - Understand the monitoring architecture
- [Monitoring user guide](/docs/user-guides/render-farm-monitoring-guide/) - Configure dashboards and alerts
- [Monitoring reference](/docs/reference/monitoring-reference/) - Complete configuration reference
