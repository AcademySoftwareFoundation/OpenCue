---
title: "Deploying the Distributed Scheduler"
nav_order: 22
parent: Getting Started
layout: default
linkTitle: "Deploying the Distributed Scheduler"
date: 2025-12-12
description: >
  Deploy the Distributed Scheduler to scale OpenCue frame dispatching
---

# Deploying the Distributed Scheduler

### Deploy the standalone Rust scheduler for improved scalability

---

This guide shows you how to deploy the **Distributed Scheduler**, a standalone Rust module that offloads frame dispatching workload from Cuebot, enabling OpenCue to scale to larger render farms.

## What is the Distributed Scheduler?

The Distributed Scheduler is a high-performance Rust service that handles frame-to-host matching and dispatching. Unlike Cuebot's traditional reactive booking system (which responds to each host report), the scheduler operates proactively with an internal loop that continuously searches for pending jobs and intelligently matches them with cached host availability.

### Key Benefits

- **Reduced Database Load**: Host information is cached in memory, dramatically reducing complex booking queries
- **Improved Dispatch Latency**: Proactive matching reduces time-to-first-frame for new jobs
- **Horizontal Scalability**: Multiple scheduler instances can share the load by processing different clusters
- **Better Resource Utilization**: Sophisticated in-memory matching algorithms optimize host selection

For more technical details, see the [Scheduler Technical Reference](/docs/reference/scheduler).

## System Requirements

To plan your installation of the Distributed Scheduler, consider the following:

- **Memory**: Minimum 2GB RAM per scheduler instance (scales with number of hosts cached)
- **CPU**: 2-4 cores recommended per instance
- **Network**: Low-latency connection to the OpenCue database (same requirements as Cuebot)
- **Database**: PostgreSQL with the same schema as Cuebot (no additional tables required)

## Architecture Overview

The scheduler is organized around **clusters**, which represent unique combinations of:

- **Allocation Clusters**: One per facility + show + allocation tag
- **Manual Tag Clusters**: Groups of manual tags (chunk size configurable)
- **Hostname Tag Clusters**: Groups of hostname tags (chunk size configurable)

Each scheduler instance processes one or more clusters in a round-robin fashion. In distributed deployments, different instances handle different clusters to share the workload.

## Before You Begin

Before deploying the scheduler, ensure you have:

1. **Running OpenCue infrastructure**:
   - PostgreSQL database (same as used by Cuebot)
   - Cuebot instance (version 0.23.0 or later for exclusion list support)
   - RQD agents on render hosts

2. **Network access**:
   - Scheduler needs database access (same credentials as Cuebot)
   - Scheduler needs gRPC access to RQD hosts (default port 8444)

3. **Installation method**:
   - Docker (recommended for production) - install [Docker](https://www.docker.com/)
   - Pre-built binary (for testing/development)
   - Build from source (for customization)

## Installation Options

### Option 1: Run with Docker (Recommended)

The easiest way to deploy the scheduler in production is using the pre-built Docker image.

#### 1. Download the Docker Image

```bash
docker pull opencue/scheduler
```

#### 2. Create a Configuration File

Create `/etc/cue-scheduler/scheduler.yaml` with your environment-specific settings:

```yaml
logging:
  level: info,sqlx=warn

database:
  pool_size: 20
  db_host: your-postgres-host
  db_name: cuebot
  db_user: cuebot
  db_pass: your_password
  db_port: 5432

rqd:
  grpc_port: 8444
  dry_run_mode: false  # Set to true for testing without actual dispatch

queue:
  monitor_interval: 5s
  worker_threads: 4
  dispatch_frames_per_layer_limit: 20
  manual_tags_chunk_size: 100
  hostname_tags_chunk_size: 300

scheduler:
  # Optional: Filter to a specific facility
  # facility: spi
  
  # Process these allocation clusters (show:tag format)
  alloc_tags:
    - show: myshow
      tag: general
    - show: anothershow
      tag: priority
  
  # Process these manual tags
  manual_tags:
    - urgent
    - desktop
```

#### 3. Run the Scheduler Container

```bash
docker run -d \
  --name opencue-scheduler \
  --restart unless-stopped \
  -v /etc/cue-scheduler/scheduler.yaml:/etc/cue-scheduler/scheduler.yaml:ro \
  -p 9090:9090 \
  opencue/scheduler
```

The scheduler will:
- Read configuration from the mounted YAML file
- Expose Prometheus metrics on port 9090
- Automatically restart if it crashes

### Option 2: Build and Run with Docker from Source

If you need to customize the scheduler or are developing locally:

#### 1. Check Out the Source Code

Make sure you've [checked out the source code](/docs/getting-started/checking-out-the-source-code) and your current directory is the root of the checked out source.

#### 2. Build the Docker Image

```bash
docker build -t opencue/scheduler -f rust/Dockerfile.scheduler .
```

This multi-stage build:
- Compiles the Rust scheduler in release mode
- Creates a minimal runtime image with just the binary
- Includes necessary runtime dependencies

#### 3. Run the Container

Follow the same steps as Option 1, step 3 above.

### Option 3: Run Pre-built Binary

For testing or development environments:

#### 1. Download the Binary

Download the appropriate pre-built binary from the [OpenCue releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases):

- **Linux (GNU)**: `cue-scheduler-VERSION-x86_64-unknown-linux-gnu`
- **Linux (MUSL)**: `cue-scheduler-VERSION-x86_64-unknown-linux-musl` (static, no dependencies)
- **macOS (Intel)**: `cue-scheduler-VERSION-x86_64-apple-darwin`
- **macOS (Apple Silicon)**: `cue-scheduler-VERSION-aarch64-apple-darwin`

#### 2. Make Executable and Install

```bash
chmod +x cue-scheduler-VERSION-PLATFORM
sudo mv cue-scheduler-VERSION-PLATFORM /usr/local/bin/cue-scheduler
```

#### 3. Create Configuration

Create `~/.config/cue-scheduler/scheduler.yaml` (or any path you prefer).

See the sample configuration in Option 1, step 2 above.

#### 4. Run the Scheduler

```bash
# With default config location
cue-scheduler

# Or specify config path
OPENCUE_SCHEDULER_CONFIG=/path/to/scheduler.yaml cue-scheduler

# Or use command-line overrides
cue-scheduler \
  --facility spi \
  --alloc_tags=show1:general,show2:priority \
  --manual_tags=urgent,desktop
```

### Option 4: Build from Source

For development or customization:

#### 1. Install Prerequisites

**Rust toolchain**:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Protobuf compiler**:

```bash
# macOS
brew install protobuf

# Ubuntu/Debian
sudo apt-get install protobuf-compiler

# RHEL/CentOS/Rocky
sudo yum install protobuf-compiler
```

#### 2. Build the Scheduler

```bash
cd OpenCue/rust
cargo build --release -p scheduler
```

The binary will be at `target/release/cue-scheduler`.

#### 3. Run

```bash
target/release/cue-scheduler --facility spi --alloc_tags=show:general
```

## Configuring Cuebot Exclusion List

To prevent Cuebot and the Scheduler from competing for the same work, you must configure Cuebot to exclude the clusters handled by the scheduler.

### Understanding Exclusion Configuration

Cuebot supports two exclusion mechanisms in `opencue.properties`:

1. **Global Booking Disable**: Turn off all booking in Cuebot
   ```properties
   dispatcher.turn_off_booking=true
   ```

2. **Selective Exclusion**: Skip specific show:facility.allocation combinations
   ```properties
   dispatcher.exclusion_list=show1:facility.alloc1,show2:facility.alloc2
   ```

### Migration Strategy

We recommend a **gradual migration** approach:

#### Phase 1: Test with One Cluster

1. **Deploy scheduler** for a single, low-priority allocation:
   ```bash
   cue-scheduler --facility spi --alloc_tags=testshow:test
   ```

2. **Configure Cuebot exclusion**:
   ```properties
   # In opencue.properties
   dispatcher.exclusion_list=testshow:spi.test
   ```

3. **Monitor both systems**:
   - Watch scheduler metrics at `http://scheduler-host:9090/metrics`
   - Verify Cuebot logs show exclusion working
   - Confirm frames dispatch successfully

#### Phase 2: Expand Coverage

1. **Add more allocations** to scheduler:
   ```yaml
   scheduler:
     alloc_tags:
       - show: testshow
         tag: test
       - show: mainshow
         tag: general
       - show: mainshow
         tag: priority
   ```

2. **Update Cuebot exclusion list**:
   ```properties
   dispatcher.exclusion_list=testshow:spi.test,mainshow:spi.general,mainshow:spi.priority
   ```

#### Phase 3: Full Migration (Optional)

Once confident, disable Cuebot booking entirely:

```properties
dispatcher.turn_off_booking=true
```

At this point, all dispatching is handled by the scheduler.

### Exclusion List Format

The exclusion list uses the format: `show:facility.allocation`

**Examples**:

```properties
# Single allocation
dispatcher.exclusion_list=myshow:spi.general

# Multiple allocations
dispatcher.exclusion_list=show1:spi.general,show1:spi.priority,show2:la.render

# Manual and hostname tags are NOT excluded via this list
# They don't belong to specific allocations, so configure them separately in scheduler
```

**Important Notes**:

- Manual tags and hostname tags are processed by the scheduler but are NOT part of the exclusion list (they don't have allocation associations)
- Configure manual/hostname tags via the scheduler's `manual_tags` configuration
- The exclusion list only applies to allocation-based clusters

## Configuration Reference

### Database Settings

```yaml
database:
  pool_size: 20          # Connection pool size (default: 20)
  db_host: localhost     # PostgreSQL host
  db_name: cuebot        # Database name
  db_user: cuebot        # Database user
  db_pass: password      # Database password
  db_port: 5432          # PostgreSQL port
```

### Scheduler Cluster Selection

```yaml
scheduler:
  # Optional: Filter clusters to a specific facility
  facility: spi
  
  # Allocation clusters to process (show:tag format)
  alloc_tags:
    - show: myshow
      tag: general
    - show: myshow
      tag: priority
  
  # Manual tags to process (not tied to allocations)
  manual_tags:
    - urgent
    - desktop
  
  # Tags to ignore (exclude from all cluster types)
  ignore_tags:
    - deprecated_tag
    - old_allocation
```

### Queue and Performance Tuning

```yaml
queue:
  monitor_interval: 5s                      # How often to check for work
  worker_threads: 4                         # Concurrent workers
  dispatch_frames_per_layer_limit: 20       # Max frames per layer per cycle
  manual_tags_chunk_size: 100               # Manual tags per cluster
  hostname_tags_chunk_size: 300             # Hostname tags per cluster
  host_candidate_attemps_per_layer: 10      # Host matching retries
  job_back_off_duration: 300s               # Backoff after failures
  
  # Optional: Exit after N idle cycles (useful for testing)
  # empty_job_cycles_before_quiting: 10
```

### Host Cache Configuration

```yaml
host_cache:
  concurrent_groups: 3            # Parallel cache groups
  memory_key_divisor: 2GiB        # Memory bucketing granularity
  checkout_timeout: 12s           # Host checkout timeout
  monitoring_interval: 1s         # Cache monitoring frequency
  group_idle_timeout: 10800s      # Evict idle cache after 3 hours
```

### Command-Line Overrides

CLI arguments override YAML configuration:

```bash
cue-scheduler \
  --facility spi \
  --alloc_tags=show1:general,show2:priority \
  --manual_tags=urgent,desktop \
  --ignore_tags=deprecated,old
```

## Monitoring the Scheduler

### Prometheus Metrics

The scheduler exposes metrics on port 9090 at `/metrics`:

```bash
curl http://localhost:9090/metrics
```

**Key Metrics**:

- `scheduler_jobs_queried_total` - Total jobs fetched from database
- `scheduler_jobs_processed_total` - Total jobs successfully processed
- `scheduler_frames_dispatched_total` - Total frames dispatched to hosts
- `scheduler_candidates_per_layer` - Distribution of hosts needed per layer
- `scheduler_time_to_book_seconds` - Latency from frame creation to dispatch
- `scheduler_no_candidate_iterations_total` - Failed matching attempts

### Log Output

The scheduler uses structured logging. Configure verbosity:

```yaml
logging:
  level: info              # Options: trace, debug, info, warn, error
  # Or filter specific modules:
  level: info,sqlx=warn    # Reduce sqlx noise
```

**Example output**:

```
2025-12-12T10:00:00.123Z INFO scheduler: Starting scheduler feed
2025-12-12T10:00:01.456Z DEBUG scheduler: Found job: Job(id=abc123, name=render_shot_010)
2025-12-12T10:00:02.789Z DEBUG scheduler: Layer layer_id fully consumed.
2025-12-12T10:00:03.012Z INFO scheduler: Processed 5 layers, dispatched 120 frames
```

## Verifying Your Installation

### 1. Check Scheduler Startup

If running in Docker:
```bash
docker logs opencue-scheduler
```

You should see:
```
Starting scheduler feed
```

### 2. Verify Database Connectivity

The scheduler will log errors if it can't connect to PostgreSQL:

```
ERROR Failed to connect to database: connection refused
```

### 3. Monitor Frame Dispatch

Watch the metrics endpoint:
```bash
watch -n 1 'curl -s http://localhost:9090/metrics | grep scheduler_frames_dispatched_total'
```

### 4. Check Cuebot Exclusion

In Cuebot logs, verify exclusions are working:
```bash
docker logs cuebot | grep exclusion
```

## Production Deployment Recommendations

### Running as a System Service

For non-Docker deployments, create a systemd service:

**`/etc/systemd/system/opencue-scheduler.service`**:
```ini
[Unit]
Description=OpenCue Distributed Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=opencue
Group=opencue
Environment=OPENCUE_SCHEDULER_CONFIG=/etc/cue-scheduler/scheduler.yaml
ExecStart=/usr/local/bin/cue-scheduler
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable opencue-scheduler
sudo systemctl start opencue-scheduler
sudo systemctl status opencue-scheduler
```

### Resource Allocation

For production deployments:

- **Single instance**: 2-4 CPU cores, 4-8GB RAM (handles thousands of hosts)
- **Multi-instance**: Divide clusters across instances based on workload
- **Database**: Ensure connection pool size × instances < PostgreSQL max_connections

### High Availability

Currently (v1.0), the scheduler doesn't have built-in HA. For resilience:

1. Run with systemd/Docker restart policies
2. Monitor with health checks on the metrics endpoint
3. Use process supervisors (systemd, supervisord, Kubernetes)

Future releases will include automatic cluster distribution for true multi-instance HA.

## Troubleshooting

### Scheduler Not Dispatching Frames

**Check**:
1. Database connectivity: `psql -h dbhost -U cuebot -d cuebot -c "SELECT 1"`
2. Cluster configuration: Ensure `alloc_tags` matches show/allocation in database
3. Cuebot exclusion: Verify Cuebot isn't still booking the same clusters
4. RQD connectivity: Ensure scheduler can reach RQD gRPC port (8444)

### High Database Load

**Solutions**:
- Reduce `database.pool_size`
- Increase `queue.monitor_interval` (check less frequently)
- Reduce `queue.worker_threads`

### Memory Growth

**Solutions**:
- Lower `host_cache.group_idle_timeout` to evict cache sooner
- Reduce `queue.concurrent_groups` in host cache
- Monitor with `docker stats` or system tools

### Frames Failing to Dispatch

**Check logs for**:
- `AllocationOverBurst`: Allocation has exceeded its burst limit
- `HostLock`: Failed to acquire lock (another scheduler instance has a lock on the host)
- `GrpcFailure`: RQD communication failure

## Current Limitations

### Version 1.0 Constraints

- **Manual cluster assignment**: You must specify which clusters each instance handles
- **No automatic distribution**: Cluster workload isn't automatically balanced across instances
- **Single instance recommended**: While multi-instance is supported, it requires careful manual configuration

### Future Enhancements

Planned for future releases:

- **Automatic cluster distribution**: Central control module to coordinate multiple schedulers
- **Dynamic scaling**: Automatically add/remove instances based on workload
- **Self-healing**: Redistribute clusters when instances fail
- **Load balancing**: Evenly distribute work across available schedulers

## What's Next?

- [Scheduler Technical Reference](/docs/reference/scheduler) - Deep dive into architecture
- [Deploying RQD](/docs/getting-started/deploying-rqd) - Set up render hosts
- [Monitoring Jobs](/docs/user-guides/monitoring-jobs) - Track job progress

## Getting Help

- **Slack**: Join #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub Issues**: [Report bugs or request features](https://github.com/AcademySoftwareFoundation/OpenCue/issues)
- **Discussions**: [Community Q&A](https://github.com/AcademySoftwareFoundation/OpenCue/discussions)
