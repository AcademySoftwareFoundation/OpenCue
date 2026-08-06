---
title: "Distributed Scheduler Technical Reference"
nav_order: 100
parent: Reference
layout: default
linkTitle: "Distributed Scheduler"
date: 2026-05-29
description: >
  Technical reference for the OpenCue Distributed Scheduler architecture and implementation
---

# Distributed Scheduler Technical Reference

### Deep dive into the Rust-based distributed frame dispatching system

---

## Overview

The **Distributed Scheduler** (`rust/crates/scheduler/`) is a standalone Rust service that fundamentally reimagines OpenCue's frame dispatching architecture. Rather than reacting to host reports like Cuebot's traditional booking system, the scheduler operates through an internal proactive loop that continuously searches for pending work and intelligently matches it with cached host availability.

Conceptually, every dispatch is an instance of **multi-dimensional bin packing**: the scheduler must fit a frame (an item with `(cores, memory, gpus)` requirements) into a host (a bin with `(idle_cores, idle_memory, idle_gpus)` capacity). The host cache's B-tree index turns this into an O(log n) lookup, and the [`HostBookingStrategy`](#booking-strategies-bin-packing-heuristics) flags select between classical heuristics (Best-Fit vs. Worst-Fit) on each dimension independently.

Per-show resource accounting (subscription burst, folder caps, job caps) is enforced on the hot path through an **in-memory accounting store** inside the scheduler, kept fresh by a PostgreSQL `LISTEN/NOTIFY` feed from Cuebot - see the [Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/) for the full design.

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
3. **Intelligent matching** → Find hosts for frames (not frames for hosts) a 2D
   bin-packing lookup against the host B-tree
4. **Atomic accounting** → Enforce per-show / per-folder / per-job limits via a single
   lock-guarded check-and-increment in an in-memory store on the hot path
5. **Parallel dispatch** → Execute multiple dispatches concurrently

**Key Insight**: By caching host state in memory and querying jobs (not hosts), the
scheduler dramatically reduces database load. Moving the accounting hot path off
Postgres into an in-process store removes the remaining lock-contention bottleneck.
The host-side placement becomes a tunable bin-packing heuristic (see
[Booking Strategies](#booking-strategies-bin-packing-heuristics)) rather than a
hard-coded scan.

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

#### Booking Strategies: Bin-Packing Heuristics

The host cache's dual-indexed B-tree is not just an implementation detail it is a
deliberate encoding of a **two-dimensional bin-packing problem** that lets the scheduler
select between classical packing heuristics with a single config flip.

##### Framing the problem

At any moment the scheduler holds a collection of bins (hosts) of varying capacity, and
must place items (frames) into them. A frame's requirement is a vector
`(cores_min, mem_min, gpus_min, gpu_mem_min)`; a host's free capacity is the vector
`(idle_cores, idle_memory, idle_gpus, idle_gpu_mem)`. A placement is feasible only if
the item vector is component-wise ≤ the bin vector. Among the feasible bins, the
scheduler must choose one and that choice is what `HostBookingStrategy` controls.

This is the classic **Vector Bin Packing (VBP)** problem: NP-hard in general, but very
well-studied with online heuristics that are cheap to compute and produce near-optimal
packings on real workloads. The scheduler does not attempt to solve VBP optimally; it
applies a per-dimension heuristic at each booking, which is both fast and incremental
(no replanning when a host arrives or leaves).

##### The four canonical heuristics

The bin-packing literature names four primary online strategies. The scheduler exposes
two of them, applied independently per dimension:

| Heuristic | What it does | Effect |
|---|---|---|
| **First-Fit (FF)** | Place item in the first bin where it fits, in arrival order | Cheap; fragmentation depends on host arrival order |
| **Best-Fit (BF)** | Place item in the bin where remaining slack after placement is minimal | Tight packing; preserves large bins for large items; lower fragmentation |
| **Worst-Fit (WF)** | Place item in the bin with the most free space | Maximum slack for the item; spreads load; lower per-item failure rate at runtime |
| **Next-Fit (NF)** | Place in the currently-open bin; open a new one if it doesn't fit | Useful for streaming; not relevant here (hosts pre-exist) |

The scheduler implements **Best-Fit** (`*_saturation: true`) and **Worst-Fit**
(`*_saturation: false`), per dimension. First-Fit and Next-Fit are not exposed the
B-tree indexing makes Best-Fit / Worst-Fit as cheap as First-Fit while giving better
packings on heterogeneous host fleets.

##### How the B-tree encodes the heuristic

The host index is `BTreeMap<CoreKey, BTreeMap<MemoryKey, HashSet<HostId>>>`. To find
a feasible host for `(cores, memory)`, the cache walks the outer tree starting at
`range(core_key..)` (ascending core capacities) this is the standard "find smallest
≥ requirement" B-tree query, O(log n).

The strategy flips then control the **direction of iteration** on each axis:

```rust
// src/host_cache/cache.rs (paraphrased)
let mut iter = if !self.strategy.core_saturation {
    // Worst-Fit on cores: walk from largest core capacity downward
    Box::new(host_index_lock.range(core_key..).rev())
} else {
    // Best-Fit on cores: walk from smallest sufficient capacity upward
    Box::new(host_index_lock.range(core_key..))
};

iter.find_map(|(_, hosts_by_memory)| {
    if self.strategy.memory_saturation {
        // Best-Fit on memory: smallest sufficient memory bucket first
        hosts_by_memory.range(memory_key..).find_map(find_fn)
    } else {
        // Worst-Fit on memory: largest memory bucket first
        hosts_by_memory.range(memory_key..).rev().find_map(find_fn)
    }
})
```

The flag's name (`*_saturation`) describes the operator intent "saturate (fill up)
this dimension before opening fresh capacity" which is exactly what Best-Fit does.
Worst-Fit (`*_saturation: false`) leaves the dimension as slack as possible.

##### The four strategy combinations

Because the flags are independent, the scheduler supports four distinct packings:

| `core_saturation` | `memory_saturation` | Packing strategy | When to use |
|---|---|---|---|
| `true` | `false` | **Best-Fit cores, Worst-Fit memory** (default) | Render farms where most frames are core-bound but spike in memory. Tight core packing keeps big hosts free for big jobs; generous memory headroom prevents OOM kills on under-estimated frames. |
| `true` | `true` | **Best-Fit on both** classical 2D Best-Fit Decreasing | Maximum density. Best when frame memory estimates are reliable (e.g., re-rendering known sequences). Minimises fragmentation; risks tight memory if estimates are off. |
| `false` | `false` | **Worst-Fit on both** | Spreads load aggressively. Good for interactive / preview workloads where you want each frame to land on the least-loaded host available. Leaves the most slack for runtime growth. |
| `false` | `true` | **Worst-Fit cores, Best-Fit memory** | Niche: memory-constrained pools where you want to pack memory tightly but keep core headroom (e.g., compositing layers that hyperthread well). |

The default Best-Fit cores, Worst-Fit memory is the production choice at SPI and
encodes a well-known render-farm heuristic: **CPU is the constrained resource you want
to keep dense; RAM is the resource you want to keep loose because frame memory is
notoriously hard to estimate.** Flipping `memory_saturation` to `true` makes sense only
when memory estimates are trustworthy.

##### Configuration

```yaml
queue:
  host_booking_strategy:
    core_saturation: true        # Best-Fit on cores
    memory_saturation: false     # Worst-Fit on memory
```

Default in `HostBookingStrategy::default()` (`config/mod.rs:211`):
```rust
core_saturation: true
memory_saturation: false
```

##### Why this is cheap

A naive Best-Fit / Worst-Fit on N hosts is O(N) per dispatch. The B-tree gives O(log N)
because the index is pre-sorted on both keys. The `range(key..)` and `.rev()` operations
walk only as far as the first feasible host that passes the validation closure
(allocation limits, tags, OS) typically the very first one, since the index is sorted
exactly the way the heuristic wants to scan it.

The validation closure (`fn validate_match`) runs inside the iterator, so unsuitable
hosts (wrong tag, allocation over burst, OS mismatch) are skipped without removing them
from the cache. The atomic check-and-remove (`atomic_remove_if_valid`, see
[Checkout/Checkin Flow](#checkoutcheckin-flow)) then commits the placement.

##### Caveats

- **Memory is bucketed.** The `memory_key_divisor` (default 2 GiB) means hosts with
  10 GiB and 11 GiB land in the same memory bucket. Within a bucket, ordering is by
  `HashSet` iteration order (effectively undefined). For most workloads the bucket
  granularity is fine; if you need finer placement, lower the divisor at the cost of
  more B-tree nodes.
- **GPU is not indexed.** GPUs are validated in the closure, not indexed in the B-tree.
  GPU-heavy fleets fall back to scanning candidates; if this becomes a bottleneck, a
  third B-tree dimension would be the fix.
- **Strategy is global.** The flag is set once for the whole scheduler instance, not
  per show or per layer. Mixed-strategy deployments today require running separate
  scheduler instances pinned to different cluster sets.

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

### 6. In-Memory Accounting Subsystem

**Location**: `src/accounting/`

The accounting subsystem tracks how much of each resource pool (subscription, folder,
job) is currently booked. Every dispatch decision the scheduler makes is gated on these
counters if a job is already at its `int_max_cores`, the scheduler must not book another
frame against it.

Historically these counters lived only in PostgreSQL and were updated transactionally
by Cuebot on every booking and release. As the Rust scheduler took over dispatch, the
hot path was hammering the same accounting rows Cuebot's `HostReportHandler` writes to,
and lock waits on `subscription`, `folder_resource`, and `job_resource` started
limiting throughput.

The current design moves the hot path off PG locks with an **in-memory `Store`** that is the single source
of truth for booked counters: there is exactly one writer and reader, and the booking
check-and-increment is atomic under one lock. PostgreSQL remains the durable record (the
`proc` rows), and Cuebot feeds live releases and cap changes via `LISTEN/NOTIFY`.

#### Per-show ownership

The `show.b_scheduler_managed` boolean (added in migration `V45__show_scheduler_managed.sql`)
selects who owns the accounting write path for a given show:

- `false` (default): **Cuebot-managed**. Cuebot's dispatcher books and releases against
  PG accounting tables transactionally, exactly as before. The scheduler's store is not
  consulted.
- `true`: **Scheduler-managed**. The Rust scheduler books against its in-memory store on
  the hot path; Cuebot's release path only deletes the `proc` row and emits an
  `acct_release` notification. PG accounting tables for this show are refreshed by the
  scheduler's recompute loop (so CueGUI stays current).

The flag replaces the older `dispatcher.exclusion_list` and
`dispatcher.scheduler_manages_resources` properties in `opencue.properties` (both
removed). Operators toggle ownership via:

```bash
cueadmin -show <name> -setSchedulerManaged true
cueadmin -show <name> -setSchedulerManaged false
```

#### Hot path: lock-guarded check-and-increment

The per-frame booking is an in-process atomic operation in `Store::book`, under a single
lock:

```text
1. If cores > 0: check subscription burst, folder int_max_cores, job int_max_cores
2. If gpus  > 0: check folder int_max_gpus, job int_max_gpus
3. If OK: increment the three enforced vertices, record the delta as `pending`, return Applied
4. If over a limit: return LimitExceeded { table, current, limit }
5. Then transactionally INSERT proc in Postgres (outside the lock)
```

Only the three enforced vertices are tracked (subscription, folder, job); layer and
point have no hot-path cap and are not kept in the store. On limit-check failure the
rejection is attributed to the responsible table via
`scheduler_accounting_limit_exceeded_total{table=...}` metrics.

After the `proc` transaction commits and RQD launches, the dispatcher calls `confirm`
(drops the `pending` portion, keeps the booked increment). If the INSERT or launch
fails, it calls `rollback` (undoes both). Exactly one runs per successful booking.

#### Live feed: PostgreSQL LISTEN/NOTIFY

Cuebot emits two notifications, each `pg_notify` in the **same transaction** as the PG
write it describes (delivered iff that write commits no partial-failure window):

- `acct_release`: a per-proc release delta on `procDestroyed` for scheduler-managed
  shows. The scheduler decrements the three vertices.
- `acct_limit_change`: an enforced cap change (subscription burst, folder/job max
  cores/gpus) from a cueadmin operation. The scheduler updates the cap in the store.

The scheduler listens on a dedicated connection and reconnects on drop; anything missed
during the gap is healed by the backstop loops below.

#### Backstop loops

- **Recompute (every 15 s)**: overwrites the store's booked counters from `SUM(proc)`,
  carrying each key's in-flight `pending` delta forward so a just-booked frame is never
  erased (the one way an absolute overwrite could under-count and over-book). Also
  rewrites the PG accounting tables for CueGUI. **No CAS, no retry** the live store is
  the primary record.
- **Limit reseed (every 5 min)**: re-reads the enforced caps from PG into the store
  the backstop for any missed `acct_limit_change`.
- **Bootstrap reseed (blocking at startup)**: seeds caps then counters from PG before
  the pipeline accepts work. The store is the only copy, so this gate is mandatory.

#### Cuebot integration

`ProcDaoJdbc.procDestroyed` checks `b_scheduler_managed` on every release. For
scheduler-managed shows it `DELETE`s the proc row and issues
`AccountingNotifier.notifyRelease` in the same transaction. A kill-switch property
`accounting.notify.enabled` (default true) disables the notifications; flag-off degrades
to recompute-only, which is the **safe** direction (no decrements → counters read high →
under-book → healed by recompute), so there is no startup guardrail only a WARN and a
`cuebot_accounting_notify_disabled` metric for ops visibility.

#### Source files

| Path | Purpose |
|---|---|
| `accounting/mod.rs` | Module root; `apply_booking` / `confirm_booking` / `rollback_booking` facade |
| `accounting/store.rs` | In-memory counters + caps; the locked atomic `book` / `confirm` / `rollback` |
| `accounting/listener.rs` | `PgListener` on `acct_release` + `acct_limit_change` |
| `accounting/recompute.rs` | 15 s `SUM(proc)` → PG tables + store overwrite with pending carry-forward |
| `accounting/limit_reseed.rs` | 5 min caps → store |
| `accounting/bootstrap.rs` | Blocking startup reseed |
| `accounting/managed_shows.rs` | Cached lookup of scheduler-managed shows + managed-flip seed |
| `accounting/booking_delta.rs` | Per-booking delta carried through the dispatch pipeline |
| `accounting/dao.rs` | PG queries used by the reseeds |
| `accounting/error.rs` | `AccountingError::LimitExceeded` |

**For the full design** source-of-truth model, the pending carry-forward and the
straddle-window race it closes, NOTIFY payload shapes, failure modes, the kill-switch,
and the N=1 assumption see the
[Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/).

### 7. Metrics and Observability

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

**Show selection** is driven solely by the `show.b_scheduler_managed` boolean DB column
(toggled with `cueadmin -scheduler-managed <show> on|off`). The scheduler automatically
loads *all* clusters — allocation, manual-tag, hostname-tag, and hardware host-tag — for
every show where `b_scheduler_managed = true`. There is no per-show, per-allocation, or
per-tag selection in the config; a show is wholly scheduler-managed or wholly
Cuebot-managed.

**Facility**:
```yaml
scheduler:
  facility: spi
```

Optionally scopes the instance to one facility's scheduler-managed clusters.

**Ignore Tags**:
```yaml
scheduler:
  ignore_tags:
    - deprecated_tag
```

Filters out specified tags from all loaded clusters before processing.

**Cluster Reload Interval**:
```yaml
queue:
  cluster_reload_interval: 120s
```

Interval between full reloads of the cluster set from the DB. The scheduler periodically
rebuilds the set of clusters from all currently-managed shows and swaps the live set only
when it actually changed, so flipping `b_scheduler_managed` (and host-tag / subscription
changes) is picked up without a restart. Default: 120s.

The manual-tag and hostname-tag chunk sizes (`queue.manual_tags_chunk_size`,
`queue.hostname_tags_chunk_size`) control how DB-loaded host-tags are grouped into
clusters (see [Cluster System](#1-cluster-system)).

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

### Booking Strategy (Bin-Packing)

```yaml
queue:
  host_booking_strategy:
    core_saturation: true        # Best-Fit on cores; false = Worst-Fit
    memory_saturation: false     # Worst-Fit on memory; true = Best-Fit
```

See [Booking Strategies: Bin-Packing Heuristics](#booking-strategies-bin-packing-heuristics)
for the full mapping from flag values to packing strategies and the workloads each fits.
The default (Best-Fit cores, Worst-Fit memory) is the right choice for most render
farms only flip `memory_saturation` if frame memory estimates are trustworthy.

### Accounting

```yaml
accounting:
  recompute_interval: 15s
  limit_reseed_interval: 300s
  managed_shows_ttl: 30s
```

- **`recompute_interval`** (default 15s): how often to overwrite the in-memory booked
  counters from `SUM(proc)` (carrying in-flight bookings forward) and refresh the PG
  accounting tables CueGUI reads. This is the primary utilization backstop now that
  releases arrive live via NOTIFY, so it runs frequently. Lower = tighter convergence;
  higher = less DB load.
- **`limit_reseed_interval`** (default 300s): how often to re-read the enforced caps
  (subscription burst, folder/job max cores/gpus) from PG into the store. The
  `acct_limit_change` NOTIFY propagates cueadmin changes immediately; this is the
  backstop for any missed notification.
- **`managed_shows_ttl`** (default 30s): how often the cache of `b_scheduler_managed`
  shows is refreshed.

The accounting store needs only PostgreSQL; no other external store is required. The
matching Cuebot side emits the live feed when `accounting.notify.enabled=true` (default),
riding the existing PG connection.

## Distributed Operation

### Current Architecture (v1.0)

The scheduler supports distributed operation by scoping each instance to a facility with
`--facility`. Show ownership is selected by the per-show `b_scheduler_managed` flag, and
each instance automatically loads all clusters (allocation, manual, hostname, and
hardware host-tags) for every scheduler-managed show in its facility:

**Instance 1**:
```bash
cue-scheduler --facility spi
```

**Instance 2**:
```bash
cue-scheduler --facility lax
```

There is no hand-listing of tags or clusters. To move work onto (or off) the scheduler,
toggle the show with `cueadmin -scheduler-managed <show> on|off`; the change is picked up
on the next cluster reload (`queue.cluster_reload_interval`, default 120s) with no
restart.

**Critical**: When running multiple instances, scope them to non-overlapping facilities
to prevent two instances from owning the same clusters.

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

**In-Memory Accounting (N=1)**:
- The accounting store is in-process and **not shared**, so it assumes a single
  scheduler instance: exactly one process owns the booked counters, which is what makes
  the atomic check-and-increment and the absolute recompute correct.
- This is a deliberate trade for the structural elimination of the accounting-drift bug
  class. Running more than one scheduler that could book the same show would let two
  processes enforce against separate copies and jointly over-book a hard cap. Crossing
  N>1 requires a shared/coordinated counter (or a non-overlapping partitioning scheme)
  plus leader election for the recompute and limit-reseed loops none of which is in
  place. See the [Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/#the-n1-assumption-and-the-revisit-trigger-for-n1).

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

**Smoke tests** (requires a migrated local Postgres, see `docker compose up -d flyway`):
```bash
cargo test -p scheduler --features smoke-tests --test smoke_tests
```

**Stress tests** (requires a migrated local Postgres; see the
[Scheduler Stress Testing](/docs/developer-guide/scheduler-stress-testing/)
guide for tuning, CI behavior, and how to read the report):
```bash
cargo test -p scheduler --features stress-tests --test stress_tests -- --nocapture

# Release mode for representative benchmark numbers
cargo test -p scheduler --release --features stress-tests --test stress_tests -- --nocapture
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
- Coexists with Cuebot via the per-show `b_scheduler_managed` flag see the
  [Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/) for the
  ownership model

### Handing a show to the scheduler

The legacy `dispatcher.exclusion_list` / `dispatcher.scheduler_manages_resources`
properties are removed. Show ownership is now a per-show database flag, toggled live:

```bash
cueadmin -show <name> -setSchedulerManaged true    # move to scheduler
cueadmin -show <name> -setSchedulerManaged false   # move back to Cuebot
```

No drain or quiesce is needed in-flight bookings continue executing through whichever
release path is active at release time, and transient PG drift heals via the next
recompute (≤ 2 min). The `ShowDao` cache picks up the flag change within ~30 s.

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
samply record cargo test -p scheduler --release --features stress-tests --test stress_tests -- --nocapture
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
- **Vector Bin Packing (VBP)**: Generalisation of bin packing where each item and bin
  is described by a multi-dimensional capacity vector (cores, memory, GPUs). The
  scheduler's placement problem is an instance of online VBP.
- **Best-Fit / Worst-Fit**: Classical bin-packing heuristics. Best-Fit places an item
  in the bin where the post-placement slack is minimal (tightest fit); Worst-Fit picks
  the bin with the most free capacity.
- **HostBookingStrategy**: Per-dimension flag controlling which heuristic (Best-Fit or
  Worst-Fit) the host cache uses when scanning the B-tree for a candidate.
- **Scheduler-managed show**: A show with `b_scheduler_managed = true` dispatch and
  hot-path accounting are owned by the Rust scheduler via its in-memory store.
- **Cuebot-managed show**: A show with `b_scheduler_managed = false` legacy
  behaviour; Cuebot dispatches and updates PG accounting transactionally.
- **Pending delta**: the portion of a booked counter still in flight (proc row maybe
  not yet visible to the recompute snapshot); carried forward across a recompute so the
  absolute overwrite cannot erase a just-booked frame.
- **Recompute loop**: 15-second job that overwrites the in-memory booked counters from
  `SUM(proc) + pending` and refreshes the PG accounting tables for CueGUI.
- **Limit reseed**: 5-min job that re-reads enforced caps (burst, folder/job max
  cores/gpus) from PG into the store.
- **`acct_release` / `acct_limit_change`**: the two PG `LISTEN/NOTIFY` channels Cuebot
  emits transactionally for releases and cap changes.
