---
title: "Distributed Scheduler Technical Reference"
nav_order: 100
parent: Reference
layout: default
linkTitle: "Distributed Scheduler"
date: 2025-12-12
description: >
  Technical reference for the OpenCue Distributed Scheduler architecture and implementation
---

# Distributed Scheduler Technical Reference

### Deep dive into the Rust-based distributed frame dispatching system

---

## Overview

The **Distributed Scheduler** (`rust/crates/scheduler/`) is a standalone Rust service that fundamentally reimagines OpenCue's frame dispatching architecture. Rather than reacting to host reports like Cuebot's traditional booking system, the scheduler operates through an internal proactive loop that continuously searches for pending work and intelligently matches it with cached host availability.

This document provides technical details for developers, operators, and contributors working with the scheduler's internals.

## Architectural Philosophy

### The Reactive Problem (Traditional Cuebot)

Cuebot's traditional dispatcher operates reactively:

1. **Host reports** → Triggers `HostReportHandler`
2. **Booking query** → Complex SQL to find suitable layers for this specific host
3. **Frame dispatch** → Reserve frame, book resources, call RQD
4. **Repeat** for every host report

This creates a **database bottleneck**: every host report generates intensive booking queries, and the database's ability to handle these queries becomes the primary scaling constraint.

### The Proactive Solution (Distributed Scheduler)

The scheduler inverts this model:

1. **Continuous loop** → Query pending jobs from database
2. **Host cache** → In-memory view of available hosts (indexed by resources)
3. **Intelligent matching** → Find hosts for frames (not frames for hosts)
4. **Parallel dispatch** → Execute multiple dispatches concurrently

**Key Insight**: By caching host state in memory and querying jobs (not hosts), the scheduler dramatically reduces database load and enables horizontal scaling.

## Core Components

### 1. Cluster System

**Location**: `src/cluster.rs`

The cluster system organizes work into logical groupings for efficient distribution.

#### Cluster Types

**Allocation Clusters** (`Cluster::ComposedKey`):
- Represents: `facility_id + show_id + allocation_tag`
- One cluster per unique combination
- Example: `facility=spi, show=myshow, tag=general`
- Used for: Standard allocation-based rendering

**Tag-Based Clusters** (`Cluster::TagsKey`):
- Represents: `facility_id + [manual_tags]` or `facility_id + [hostname_tags]`
- Groups multiple tags into chunks (configurable chunk size)
- Example: `facility=spi, tags=[urgent, desktop, workstation]`
- Used for: Manual override tags and host-specific tags

#### ClusterFeed

The `ClusterFeed` is a round-robin iterator over all clusters with intelligent sleep management:

```rust
pub struct ClusterFeed {
    clusters: Arc<RwLock<Vec<Cluster>>>,
    current_index: Arc<AtomicUsize>,
    stop_flag: Arc<AtomicBool>,
    sleep_map: Arc<Mutex<HashMap<Cluster, SystemTime>>>,
}
```

**Key Features**:

- **Round-robin iteration**: Ensures fair processing across all clusters
- **Sleep mechanism**: Clusters with no work are put to sleep to avoid wasted database queries
- **Wake-up tracking**: Automatically wakes clusters after their sleep duration expires
- **Backoff strategy**: Longer sleeps when all clusters are idle, shorter when some are active
- **Control messages**: `FeedMessage::Sleep` and `FeedMessage::Stop` for runtime control

**Load Algorithm**:

```rust
pub async fn load_all(facility_id: &Option<Uuid>, ignore_tags: &[String]) -> Result<Self>
```

1. Query all tags from database (`fetch_alloc_clusters`, `fetch_non_alloc_clusters`)
2. Filter by facility (if specified) and ignore list
3. Create one cluster per allocation tag
4. Chunk manual tags (default: 100 per cluster)
5. Chunk hostname tags (default: 300 per cluster)

**Rationale**: Chunking prevents too many clusters when there are thousands of manual/hostname tags, balancing granularity with overhead.

### 2. Host Cache

**Location**: `src/host_cache/`

The host cache is a B-tree-based in-memory index of available hosts, enabling O(log n) lookups by resource requirements.

#### Architecture

**Store** (`store.rs`):
- Global `HOST_STORE`: Thread-safe `DashMap<HostId, Host>`
- Atomic operations with optimistic locking via `last_updated` timestamp
- Prevents race conditions during concurrent checkout/checkin

**Cache** (`cache.rs`):
- Per-cluster-key cache instance
- Dual-indexed B-trees: `BTreeMap<CoreKey, BTreeMap<MemoryKey, HashSet<HostId>>>`
- Enables efficient range queries: "Find hosts with >= 4 cores and >= 8GB memory"

#### Data Structures

```rust
type CoreKey = u32;           // Available cores
type MemoryKey = u64;         // Available memory (bucketed)
type MemoryBTree = BTreeMap<MemoryKey, HashSet<HostId>>;

pub struct HostCache {
    hosts_index: RwLock<BTreeMap<CoreKey, MemoryBTree>>,
    last_queried: RwLock<SystemTime>,
    last_fetched: RwLock<Option<SystemTime>>,
    strategy: HostBookingStrategy,
}
```

**Memory Bucketing**:
```rust
fn gen_memory_key(memory: ByteSize) -> MemoryKey {
    memory.as_u64() / CONFIG.host_cache.memory_key_divisor.as_u64()
}
```

- Divides memory into buckets (default: 2GB divisor)
- Example: 4GB → key 1, 8GB → key 3, 10GB → key 4
- Reduces fragmentation while maintaining efficient lookups

#### Checkout/Checkin Flow

**Checkout** (`check_out`):
1. Search B-tree for hosts with sufficient resources
2. Apply validation function (allocation limits, tags, etc.)
3. Atomically remove from `HOST_STORE` (prevents double-booking)
4. Remove from cache index
5. Return `Host` to caller

**Checkin** (`check_in`):
1. Update `HOST_STORE` with new host state
2. Index by current `idle_cores` and `idle_memory`
3. Insert into appropriate B-tree bucket

**Atomic Safety**:
```rust
pub fn atomic_remove_if_valid<F>(
    &self,
    host_id: &HostId,
    expected_last_updated: DateTime<Utc>,
    validation: F,
) -> Result<Option<Host>, ()>
where
    F: Fn(&Host) -> bool,
{
    // Compare-and-swap with timestamp verification
    // Prevents removal if host state changed since lookup
}
```

#### Booking Strategies

**Core Saturation** (`core_saturation: true`):
- Searches from minimum cores upward
- Prefers hosts with fewer idle cores
- Maximizes core utilization, leaves larger hosts for bigger jobs

**Memory Saturation** (`memory_saturation: true`):
- Searches from minimum memory upward
- Prefers hosts with less idle memory
- Packs memory efficiently

**Default Strategy**:
```yaml
host_booking_strategy:
  core_saturation: true
  memory_saturation: false
```

#### Cache Expiration

- **Group Idle Timeout**: Evict cache groups not queried within 3 hours (configurable)
- **Data Staleness**: Refresh from database when `expired()` returns true
- **Activity Tracking**: `ping_query()` updates `last_queried` on every access

### 3. Scheduling Pipeline

**Location**: `src/pipeline/`

The pipeline processes work in multiple stages, from job queries to frame dispatch.

#### Entry Point (`entrypoint.rs`)

```rust
pub async fn run(cluster_feed: ClusterFeed) -> miette::Result<()>
```

**Main Loop**:
1. Receive cluster from `ClusterFeed`
2. Query pending jobs for this cluster
3. Process jobs concurrently (configurable buffer size)
4. Dispatch frames for each job
5. Sleep cluster if no work found
6. Stop after N empty cycles (optional, for testing)

**Concurrency Control**:
```rust
.for_each_concurrent(CONFIG.queue.stream.cluster_buffer_size, |cluster| { ... })
```
- Default: 3 clusters processed in parallel
- Balances throughput with database connection pressure

#### Matching Service (`matcher.rs`)

The `MatchingService` orchestrates the core dispatch logic.

**Process Flow**:

```rust
pub async fn process(&self, job: DispatchJob)
```

1. **Query Layers**: Fetch eligible layers from database for this job
   ```rust
   self.layer_dao.query_layers(job.id, tags).await
   ```

2. **Layer Permit**: Acquire exclusive permit to prevent race conditions
   ```rust
   self.layer_permit_service.send(Request { id: layer.id, duration }).await
   ```
   - Prevents multiple scheduler instances from processing the same layer concurrently
   - Timeout: 2 seconds × number of frames in layer

3. **Process Each Layer**: Find hosts and dispatch frames
   ```rust
   async fn process_layer(&self, dispatch_layer: DispatchLayer, cluster: Arc<Cluster>)
   ```

4. **Release Permit**: Allow other schedulers to process this layer
   ```rust
   self.layer_permit_service.send(Release { id: layer.id }).await
   ```

**Host Matching Algorithm**:

```rust
async fn process_layer(&self, dispatch_layer: DispatchLayer, cluster: Arc<Cluster>)
```

1. **Filter Tags**: Match cluster tags to layer requirements
   ```rust
   fn filter_matching_tags(cluster: &Cluster, dispatch_layer: &DispatchLayer) -> Vec<Tag>
   ```

2. **Checkout Host**: Request candidate from host cache
   ```rust
   self.host_service.send(CheckOut {
       facility_id: layer.facility_id,
       show_id: layer.show_id,
       tags,
       cores: cores_requested,
       memory: layer.mem_min,
       validation: |host| Self::validate_match(host, ...),
   }).await
   ```

3. **Validate Match**: Check allocation limits, OS compatibility
   ```rust
   fn validate_match(
       host: &Host,
       layer_id: &Uuid,
       show_id: &Uuid,
       cores_requested: CoreSize,
       allocation_service: &AllocationService,
       os: Option<&str>,
   ) -> bool
   ```

4. **Dispatch Frames**: Send to RQD via gRPC
   ```rust
   self.dispatcher_service.send(DispatchLayerMessage { layer, host }).await
   ```

5. **Handle Result**:
   - **Success**: Checkin updated host, continue if frames remain
   - **Failure**: Invalidate host in cache, log error
   - **No Candidate**: Sleep layer, try again later

**Retry Logic**:
- Default: 10 host candidate attempts per layer
- Stops early on first successful dispatch
- Tracks `HOSTS_ATTEMPTED` and `WASTED_ATTEMPTS` metrics

**Concurrency Limiting**:
```rust
concurrency_semaphore: Arc::new(Semaphore::new(max_concurrent_transactions))
```
- Limits concurrent database transactions
- Prevents connection pool exhaustion
- Max: `pool_size - 1` (reserves 1 connection for monitoring)

### 4. RQD Dispatcher

**Location**: `src/pipeline/dispatcher/`

The dispatcher handles the actual frame execution via gRPC calls to RQD hosts.

#### Frame Dispatch Flow

```rust
pub async fn dispatch(
    layer: DispatchLayer,
    host: Host,
) -> Result<DispatchResult, DispatchError>
```

1. **Group Frames**: Create `FrameSet` for this host
   ```rust
   let frame_set = FrameSet::new(layer, host, cores_reserved, memory_reserved);
   ```

2. **Database Transaction**: Lock frames and book resources
   ```rust
   // Optimistic locking on frame.int_version
   frame_dao.lock_for_update(frame_ids).await?
   
   // Book proc and update resources atomically
   proc_dao.insert_proc(proc).await?
   ```

3. **gRPC Call**: Send RunFrame to RQD
   ```rust
   rqd_client.run_frame(run_frame_request).await?
   ```

4. **Update Host State**: Calculate remaining resources
   ```rust
   host.idle_cores -= cores_used;
   host.idle_memory -= memory_used;
   ```

5. **Return Updated State**: For cache checkin
   ```rust
   Ok(DispatchResult { updated_host, updated_layer })
   ```

#### Resource Calculation

**Cores**:
```rust
let cores_reserved = std::cmp::max(
    layer.cores_min,
    std::cmp::min(layer.cores_max, host.idle_cores)
);
```

**Memory**:
- Base: `layer.mem_min`
- Soft limit: `mem_min × frame_memory_soft_limit` (default: 1.6x)
- Hard limit: `mem_min × frame_memory_hard_limit` (default: 2.0x)
- Actual: Lesser of `host.idle_memory` and calculated limit

**GPU** (if required):
- Reserve `layer.gpus_min` GPUs
- Reserve `layer.gpu_mem_min` GPU memory

#### Error Handling

**Dispatch Errors**:
- `HostLock`: Failed to acquire database lock (another scheduler?)
- `AllocationOverBurst`: Allocation exceeded burst limit
- `FailedToStartOnDb`: Database error during booking
- `GrpcFailure`: RQD communication failure
- `FailedToCreateProc`: Proc creation failed

**Error Recovery**:
- **Retriable errors**: Host invalidated, retry with different host
- **Fatal errors**: Layer skipped, logged for operator review

### 5. Database Access Layer

**Location**: `src/dao/`

The DAO layer uses SQLx for async PostgreSQL queries.

#### Key DAOs

**JobDao** (`job_dao.rs`):
```rust
pub async fn query_pending_jobs_by_show_facility_tag(
    &self,
    show_id: Uuid,
    facility_id: Uuid,
    tag: String,
) -> Result<Vec<JobModel>>
```
- Fetches jobs with pending frames for a specific allocation cluster
- Ordered by priority (configurable scheduling mode in future)

**LayerDao** (`layer_dao.rs`):
```rust
pub async fn query_layers(
    &self,
    job_id: Uuid,
    tags: Vec<String>,
) -> Result<Vec<DispatchLayer>>
```
- Fetches dispatchable layers for a job
- Filters by tag requirements
- Includes frame details for dispatch

**HostDao** (`host_dao.rs`):
```rust
pub async fn fetch_hosts(
    &self,
    facility_id: Uuid,
    show_id: Uuid,
    tags: Vec<String>,
) -> Result<Vec<Host>>
```
- Fetches available hosts matching allocation and tags
- Used to populate host cache

**FrameDao** (`frame_dao.rs`):
```rust
pub async fn lock_for_update(
    &self,
    frame_ids: Vec<Uuid>,
) -> Result<Vec<FrameModel>>
```
- Acquires pessimistic locks on frames
- Prevents double-booking via `int_version` optimistic lock
- Atomically updates frame state to RUNNING

**ProcDao** (`proc_dao.rs`):
```rust
pub async fn insert_proc(
    &self,
    proc: VirtualProc,
) -> Result<()>
```
- Creates virtual proc linking frame to host
- Updates resource accounting across multiple tables

#### Connection Pooling

```yaml
database:
  pool_size: 20  # Max concurrent connections
```

**SQLx Configuration**:
- Async connection pool
- Automatic reconnection on failures
- Prepared statement caching
- Transaction support

### 6. Metrics and Observability

**Location**: `src/metrics/`

The scheduler exposes Prometheus metrics for monitoring and debugging.

#### Key Metrics

**Job Processing**:
```rust
scheduler_jobs_queried_total        // Total jobs fetched from DB
scheduler_jobs_processed_total      // Total jobs successfully processed
scheduler_frames_dispatched_total   // Total frames dispatched to hosts
```

**Performance**:
```rust
scheduler_time_to_book_seconds      // Histogram: latency from frame creation to dispatch
scheduler_job_query_duration_seconds // Histogram: database query performance
```

**Efficiency**:
```rust
scheduler_candidates_per_layer      // Histogram: host attempts needed per layer
scheduler_no_candidate_iterations_total // Counter: failed host matches
```

**Host Cache**:
```rust
scheduler_host_cache_size           // Gauge: number of cached hosts
scheduler_host_cache_hits_total     // Counter: successful checkouts
scheduler_host_cache_misses_total   // Counter: no suitable host found
```

#### Metrics Collection

Prometheus endpoint: `http://scheduler-host:9090/metrics`

**Example Query**:
```promql
# Average dispatch latency
rate(scheduler_time_to_book_seconds_sum[5m]) 
  / rate(scheduler_time_to_book_seconds_count[5m])

# Frames dispatched per second
rate(scheduler_frames_dispatched_total[1m])

# Host match efficiency
scheduler_host_cache_hits_total 
  / (scheduler_host_cache_hits_total + scheduler_host_cache_misses_total)
```

## Configuration Deep Dive

### Cluster Configuration

**Allocation Tags**:
```yaml
scheduler:
  alloc_tags:
    - show: myshow
      tag: general
```

Loads one cluster per entry: `(facility_id, show_id, "general")`

**Manual Tags**:
```yaml
scheduler:
  manual_tags:
    - urgent
    - desktop
    - workstation
```

Chunks into groups (default: 100 tags per cluster):
- Cluster 1: `(facility_id, [urgent, desktop, workstation])`
- If more than 100 tags, splits into multiple clusters

**Ignore Tags**:
```yaml
scheduler:
  ignore_tags:
    - deprecated_tag
```

Filters out specified tags from all cluster types before processing.

### Performance Tuning

**Database Pool**:
```yaml
database:
  pool_size: 20
```
- **Too low**: Limits concurrency, slower processing
- **Too high**: Exhausts PostgreSQL connections
- **Rule of thumb**: 10-20 per scheduler instance

**Worker Threads**:
```yaml
queue:
  worker_threads: 4
```
- **Too low**: Underutilizes CPU
- **Too high**: Context switching overhead
- **Rule of thumb**: 2-4 for typical workloads

**Dispatch Limits**:
```yaml
queue:
  dispatch_frames_per_layer_limit: 20
```
- Prevents single layer from monopolizing resources
- Lower: More fair distribution across layers
- Higher: Faster completion for individual layers

**Stream Buffers**:
```yaml
queue:
  stream:
    cluster_buffer_size: 3
    job_buffer_size: 3
```
- Controls concurrent processing at each pipeline stage
- Higher: More parallelism, higher memory/DB load
- Lower: More sequential, lower resource usage

### Cache Tuning

**Memory Bucketing**:
```yaml
host_cache:
  memory_key_divisor: 2GiB
```
- Larger: Fewer buckets, faster lookups, less precise matching
- Smaller: More buckets, slower lookups, more precise matching
- Default (2GB) balances precision with performance

**Idle Timeout**:
```yaml
host_cache:
  group_idle_timeout: 10800s  # 3 hours
```
- Evicts unused cache groups to free memory
- Lower: Less memory usage, more DB queries on reactivation
- Higher: Less DB churn, more memory usage

**Concurrent Groups**:
```yaml
host_cache:
  concurrent_groups: 3
```
- Number of cache groups to fetch/update in parallel
- Higher: Faster cache refresh, more DB load
- Lower: Slower refresh, less DB load

## Distributed Operation

### Current Architecture (v1.0)

The scheduler supports distributed operation via manual cluster assignment:

**Instance 1**:
```bash
cue-scheduler --alloc_tags=show1:general,show1:priority
```

**Instance 2**:
```bash
cue-scheduler --alloc_tags=show2:general,show2:priority
```

**Instance 3**:
```bash
cue-scheduler --manual_tags=urgent,desktop
```

**Critical**: Ensure no cluster overlap between instances to prevent race conditions.

### Coordination Mechanisms

**Layer Permit System**:
- Prevents concurrent processing of the same layer
- Timeout-based (default: 2 seconds × frame count)
- Stored in shared database table
- Allows multiple instances to safely coexist

**Frame Locking**:
- Optimistic locking via `frame.int_version`
- Database-level conflict resolution
- Prevents double-booking even if permits overlap

### Future Architecture (Planned)

**Control Module** (2026 roadmap):
- Central coordinator for cluster distribution
- Dynamic instance registration and heartbeat
- Automatic cluster assignment based on load
- Self-healing on instance failure
- Load balancing across instances

**Auto-scaling**:
- Spin up instances during high load
- Terminate instances during idle periods
- Cloud-native deployment (Kubernetes, ECS)

## Development Workflow

### Building

```bash
cd rust
cargo build -p scheduler
```

**Development build** (includes debug symbols):
```bash
cargo build -p scheduler
# Binary at: target/debug/cue-scheduler
```

**Release build** (optimized):
```bash
cargo build --release -p scheduler
# Binary at: target/release/cue-scheduler
```

### Testing

**Unit tests**:
```bash
cargo test -p scheduler
```

**Integration tests** (requires database):
```bash
# Set up test database
export DATABASE_URL=postgresql://user:pass@localhost/test_db

# Run integration tests
cargo test -p scheduler --test integration_tests
```

**Stress tests**:
```bash
cargo test -p scheduler --test stress_tests --release -- --nocapture
```

### Code Quality

**Linting**:
```bash
cargo clippy -p scheduler -- -D warnings
```

**Formatting**:
```bash
cargo fmt -p scheduler
```

**Documentation**:
```bash
cargo doc -p scheduler --open
```

## Migration from Cuebot Booking

### Compatibility

The scheduler:
- Uses the same PostgreSQL database schema as Cuebot
- Communicates with RQD via the same gRPC protocol
- Produces the same proc/frame state transitions
- Can coexist with Cuebot (with exclusion list configured)

### Differences

**Booking Query**:
- Cuebot: Per-host complex SQL query
- Scheduler: Per-job simple query + in-memory matching

**Resource Updates**:
- Cuebot: Updated on every host report
- Scheduler: Updated on dispatch (cached in memory)

**Dispatch Trigger**:
- Cuebot: Reactive (host report arrives)
- Scheduler: Proactive (continuous loop)

## Troubleshooting and Debugging

### Enable Debug Logging

```yaml
logging:
  level: debug
```

Or via environment:
```bash
RUST_LOG=debug cue-scheduler
```

On a running instance: 
  - Sending a SIGUSR1 toggles the logging level between debug and info excluding sqlx debug messages
  - Sending a SIGUSR2 toggles the logging level between debug and info including sqlx debug messages

### Trace Specific Modules

```bash
RUST_LOG=scheduler=debug,sqlx=warn cue-scheduler
```

### Common Issues

**No frames dispatching**:
```
DEBUG scheduler: No host candidate available for layer
```
- **Cause**: Host cache empty or no matching hosts
- **Fix**: Check host queries, verify tag configuration

**High database load**:
```
WARN sqlx: connection pool exhausted
```
- **Cause**: Too many concurrent queries
- **Fix**: Reduce `pool_size` or `worker_threads`

**Layer permit timeouts**:
```
DEBUG scheduler: Layer skipped. already being processed
```
- **Cause**: Another scheduler instance processing same layer
- **Fix**: Normal in multi-instance, adjust permit duration if excessive

**Memory growth**:
```
INFO scheduler: Host cache size: 50000 hosts
```
- **Cause**: Cache not expiring idle groups
- **Fix**: Lower `group_idle_timeout` or `memory_key_divisor`

### Profiling

**CPU profiling**:
```bash
cargo install samply
samply record cargo test --test stress_tests --release -- --nocapture
```

## API and Extensibility

### Actor System (Actix)

The scheduler uses Actix actors for concurrency:

**Host Cache Service**:
```rust
let host_service = host_cache_service().await?;
host_service.send(CheckOut { ... }).await?
```

**Dispatcher Service**:
```rust
let dispatcher = rqd_dispatcher_service().await?;
dispatcher.send(DispatchLayerMessage { ... }).await?
```

**Layer Permit Service**:
```rust
let permit_svc = layer_permit_service().await?;
permit_svc.send(Request { ... }).await?
```

### Adding New Metrics

```rust
use crate::metrics;

// Counter
metrics::increment_custom_counter("custom_metric");

// Histogram
metrics::observe_custom_duration("custom_duration_seconds", duration);

// Gauge
metrics::set_custom_gauge("custom_gauge", value);
```

### Documentation

- Code comments for complex logic
- Update this reference for architectural changes
- Add examples for new features

### Testing Requirements

- Unit tests for new functions
- Integration tests for database interactions
- Stress tests for performance-critical paths

## Glossary

- **Allocation**: Resource pool assigned to a show for rendering
- **Cluster**: Logical grouping of work (facility + show + tag)
- **Cluster Feed**: Round-robin iterator over clusters
- **Host Cache**: In-memory B-tree index of available hosts
- **Layer Permit**: Lock preventing concurrent layer processing
- **Proc (Virtual Proc)**: Booking record linking frame to host
- **Tag**: Label for allocation, manual override, or hostname targeting
- **Frame Set**: Group of frames dispatched together to a host
