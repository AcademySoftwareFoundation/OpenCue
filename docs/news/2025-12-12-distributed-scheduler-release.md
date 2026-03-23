---
layout: default
title: "December 12, 2025: Distributed Scheduler Release"
parent: News
nav_order: 1
---

# Distributed Scheduler Release

### A New Scalable Frame Dispatching Solution

#### December 12, 2025

---

We're excited to announce the release of the **Distributed Scheduler**, a new standalone Rust module that fundamentally reimagines how OpenCue handles frame dispatching at scale.

## The Challenge

Cuebot's traditional booking logic operates reactively: each host report triggers a booking query that searches for suitable layers to dispatch to the reporting host. This approach creates a significant database bottleneck where every host report generates a complex `BookingQuery`, and scaling the render farm becomes limited by the database's ability to handle these intensive queries. As farms grow larger, this database pressure becomes the primary constraint on system performance.

## The Solution: Distributed Scheduler

The new **Scheduler** module (`rust/crates/scheduler/`) is a complete architectural shift that offloads the booking workload from Cuebot. Instead of reacting to host reports, the scheduler operates through an **internal proactive loop** that continuously searches for pending jobs and intelligently matches them with a cached view of available hosts.

### Key Architectural Innovations

#### 1. Host Cache with In-Memory BTree Storage

The scheduler maintains a host caching system (`src/host_cache/`) that dramatically reduces database load:

- **Cached Host Statistics**: Host availability and resource information are fetched from the database and stored in memory, eliminating the need for repeated database queries during matching
- **BTree-Based Organization**: Hosts are organized in `BTreeMap` structures indexed by available cores and memory (`src/host_cache/cache.rs`), enabling efficient O(log n) lookups for resource-based matching
- **Expiration Strategy**: The cache automatically refreshes when stale, balancing freshness with performance
- **Checkout/Checkin Pattern**: Hosts are temporarily "checked out" during matching to prevent double-booking, then "checked in" when complete

#### 2. Intelligent Matching Algorithm

The matching service (`src/pipeline/matcher.rs`) implements a layer-to-host pairing system:

- **Resource-Aware Matching**: Automatically finds hosts with sufficient cores, memory, and GPU resources for each layer's requirements
- **Tag Filtering**: Validates allocation tags, manual tags, and hostname tags to ensure frames only run on appropriate hosts
- **Concurrency Control**: Uses semaphores to limit parallel matching operations and prevent resource contention
- **Metrics-Driven**: Tracks hosts attempted, wasted attempts, and candidates per layer for performance analysis

#### 3. Cluster-Based Organization

One of the scheduler's most useful features is its cluster system (`src/cluster.rs`), which organizes work by **show + allocation combinations**:

- **Cluster Isolation**: Each cluster represents a unique show/facility/allocation grouping, allowing multiple scheduler instances to work independently without competing
- **Round-Robin Processing**: Clusters are processed in a round-robin fashion with intelligent backoff when work is exhausted
- **Sleep Mechanism**: Individual clusters can be put to sleep when no work is available, reducing wasted cycles
- **Scalability Foundation**: This architecture enables horizontal scaling—different scheduler instances can handle different clusters without conflicts

**Cluster Types**:
- **Allocation Clusters**: One per facility + show + allocation tag combination
- **Manual Tags**: Grouped into chunks (configurable size) per facility
- **Hostname Tags**: Grouped into chunks (configurable size) per facility

#### 4. Comprehensive Metrics

The scheduler exposes Prometheus metrics (`src/metrics/`) for deep observability:

- `scheduler_jobs_queried_total`: Total jobs fetched from database
- `scheduler_jobs_processed_total`: Total jobs successfully processed
- `scheduler_frames_dispatched_total`: Total frames dispatched to hosts
- `scheduler_candidates_per_layer`: Distribution of hosts needed per layer
- `scheduler_time_to_book_seconds`: Latency from frame creation to dispatch
- `scheduler_job_query_duration_seconds`: Database query performance
- `scheduler_no_candidate_iterations_total`: Failed matching attempts

Access metrics at `http://[scheduler-host]:9090/metrics`

## Coexistence with Cuebot

To enable the Scheduler and Cuebot to run concurrently without competing for work, new configuration options were added to Cuebot (PR #2087):

### Cuebot Exclusion Controls

In `opencue.properties`:

```properties
# Turn off booking for ALL allocations
dispatcher.turn_off_booking=false

# Exclude specific show:facility.allocation combinations
dispatcher.exclusion_list=show1:facility.alloc1,show2:facility.alloc2
```

**Migration Strategy**:
1. Deploy the Scheduler with specific `--alloc_tags` and `--manual_tags`
2. Configure Cuebot's `dispatcher.exclusion_list` to skip those same tags
3. Monitor both systems to verify no overlap
4. Gradually migrate more clusters to the Scheduler
5. Eventually disable Cuebot booking entirely with `dispatcher.turn_off_booking=true`

## Performance Benefits

Early testing shows significant improvements:

- **Database Load Reduction**: Fewer complex booking queries hitting the database
- **Improved Dispatch Latency**: Proactive matching reduces time-to-first-frame for new jobs
- **Horizontal Scalability**: Multiple scheduler instances can share the load by cluster
- **Better Resource Utilization**: In-memory host cache enables more sophisticated matching algorithms

## Current Limitations and Future Roadmap

### Current Version (v1.0)

- **Manual Cluster Distribution**: Operators must manually specify which clusters each scheduler instance handles via `--alloc_tags` and `--manual_tags`
- **Single Instance Recommended**: While multi-instance deployment is supported, cluster assignment is static and requires careful configuration

### Future Development

**Automatic Cluster Distribution** (Planned for 2026):
- Central control module for coordinating multiple scheduler instances
- Dynamic cluster assignment based on workload and scheduler availability
- Automatic scaling: spin up new scheduler instances as workload increases
- Self-healing: redistribute clusters when scheduler instances fail
- Load balancing: evenly distribute work across available schedulers

**Why This Matters**: The future control module will enable truly elastic scheduling—automatically scaling from a single scheduler instance during quiet periods to dozens of instances during crunch time, all without manual intervention.

## Migration Recommendation

**For v1.0**, we recommend running the Scheduler as a **single instance** to simplify deployment and avoid cluster assignment conflicts. The architecture fully supports distributed operation, but the automation layer for multi-instance coordination will arrive in a future release.

As you grow comfortable with the scheduler and your workload demands increase, you can:
1. Deploy additional instances with non-overlapping cluster assignments
2. Monitor performance and adjust cluster distribution manually
3. Prepare for the future control module that will automate this entirely

## Get Started

- **Documentation**: [Scheduler Architecture Guide](https://docs.opencue.io/docs/reference/scheduler/)
- **Source Code**: [`rust/crates/scheduler/`](https://github.com/AcademySoftwareFoundation/OpenCue/tree/new-scheduler/rust/crates/scheduler)
- **Configuration File**: [`config/scheduler.yaml`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/new-scheduler/rust/config/scheduler.yaml)

## Community and Support

Have questions or feedback about the Distributed Scheduler?

- **Slack**: Join us in #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub Discussions**: [OpenCue Discussions](https://github.com/AcademySoftwareFoundation/OpenCue/discussions)

---

The Distributed Scheduler represents a major step forward in OpenCue's evolution, enabling render farms to scale beyond previous limitations. We're excited to see how the community leverages this new architecture to build even larger and more efficient rendering pipelines.

Happy rendering!

---

[View the Release Notes](https://github.com/AcademySoftwareFoundation/OpenCue/releases) | [GitHub Repository](https://github.com/AcademySoftwareFoundation/OpenCue) | [Documentation](https://docs.opencue.io)
