---
title: "Stranded Cores in Cuebot"
nav_order: 49
parent: User Guides
layout: default
linkTitle: "Stranded Cores in Cuebot"
date: 2025-05-11
description: >
  Handling Stranded cores on Cuebot
---

# Stranded Cores in Cuebot

## The Problem

A render host has two resources that frames consume in pairs: **CPU cores** and **memory**. The scheduler reserves both per frame based on what the layer asks for. But these resources don't deplete in lockstep — a memory-hungry frame can leave plenty of cores idle while exhausting RAM.

When idle memory drops below ~1.5 GB (`Dispatcher.java:53` — `MEM_STRANDED_THRESHHOLD = 1 GB + 512 MB`), no realistic frame can be booked on that host even if 8+ cores are still free. Those cores are **stranded** — physically idle but functionally unusable. On a render farm with thousands of hosts, this silently bleeds capacity.

## The Solution: Detect, Re-attach, Recover

Cuebot doesn't try to *prevent* stranding through perfect bin-packing — instead it **detects stranding after the fact and donates the orphaned cores to the next frame** booked on that host.

### 1. Detect at frame completion
When a frame finishes, `FrameCompleteHandler.java:535-547` checks: did this proc leave the host memory-starved with idle cores? The check (`HostDaoJdbc.java:575-584`) queries idle cores on hosts where `int_mem_idle <= MEM_STRANDED_THRESHHOLD`, rounded down to whole cores (100 units each).

Recovery is only attempted when:
- The proc isn't a local (desktop) dispatch
- The job's layer is threadable (can absorb extra cores)
- The job is still bookable
- At least 1 whole core is stranded

### 2. Mark the host
`DispatchSupportService.strandCores()` (`DispatchSupportService.java:112-120`) records the stranded count on `DispatchHost.strandedCores`, stashes it in a `ConcurrentHashMap<hostId, StrandedCores>` with a **5-second TTL** (`StrandedCores.java`) so stale entries can't accumulate, and forces the host's `threadMode` to `ALL` to encourage aggressive packing.

### 3. Donate to the next frame
When the next `VirtualProc` is built for that host (`VirtualProc.java:113-115`), the stranded cores are silently added to `coresReserved`:
```java
if (host.strandedCores > 0) {
    proc.coresReserved = proc.coresReserved + host.strandedCores;
}
```
After dispatching that one frame, `CoreUnitDispatcher.java:300-302` calls `pickupStrandedCores()` to clear the marker and `break`s out of the dispatch loop — one frame "absorbs the debt," and the host returns to normal scheduling.

## Memory-Aware Prevention (the proactive half)

Two pieces of code try to *avoid* stranding in the first place:

- **`VirtualProc.getCoreSpan()`** (`VirtualProc.java:266-284`) computes `memPerCore = host.idleMemory / totalCores` and reserves `ceil(minMemory / memPerCore)` cores — sizing the booking to the host's actual memory-per-core ratio rather than the layer's hardcoded core request.
- **Pre-emptive whole-host booking** (`VirtualProc.java:148-150`): if booking the requested memory *would* leave less than `MEM_STRANDED_THRESHHOLD` free, the proc grabs *all* remaining whole cores immediately. Better to over-allocate cores to one frame than leave them stranded.

A parallel system handles GPUs (`DispatchHost.removeGpu()` reserves 4 GB RAM + 100 cores on GPU hosts so a CPU job can't strand the GPU dispatch path).

## Observability

`DispatchSupport.java:119-134` exposes counters — `strandedCoresCount`, `pickedUpCoresCount`, and GPU equivalents — through `CueStatic.cueGetSystemStats()` so operators can see how often stranding occurs vs. is recovered.

## TL;DR

Memory exhausts before cores do, so cores get stuck. Cuebot's answer is a small feedback loop: notice stranding when a frame completes, attach the orphaned cores to the next frame booked on that host (within 5 seconds), and use memory-per-core math to size bookings sensibly in the first place. The recovery is opportunistic rather than perfect — the trade-off is simple, low-overhead code instead of a globally optimal bin-packing solver.

## A working example

Consider a 16-core / 64 GB host. Its **natural ratio** is 4 GB/core — if every frame consumed resources in that ratio, nothing would ever strand.

But layers don't request resources in that ratio. Suppose frames on this host keep asking for 8 GB and 1 core each (a memory-heavy workload):

| Step | Idle cores | Idle mem | Notes |
|---|---|---|---|
| Start | 16 | 64 GB | |
| Book 7× (8 GB / 1 core) | 9 | 8 GB | |
| Book 1× (8 GB / 1 core) | **8** | **0 GB** | 8 cores stranded |

Eight cores sit idle and **nothing can be booked here** — every layer requesting more than 0 GB is rejected. The host is functionally dead until a frame completes.

## What "donating" the stranded cores actually accomplishes

Now one of those 8 GB frames finishes:

**Without recovery**: The completed frame returns 8 GB + 1 core → host has 9 idle cores, 8 GB free. The scheduler books another 8 GB / 1 core frame. Back to 8 cores idle, 0 GB. **The strand re-forms immediately.** This repeats forever; the 8 stranded cores never do work.

**With recovery**: When the frame completes, cuebot notices the host *was* in a stranded state and marks `host.strandedCores = 8`. The next 8 GB / 1 core frame is booked, but `VirtualProc.java:113` quietly inflates its reservation to **1 + 8 = 9 cores** for the same 8 GB memory. The threadable layer now runs 9-way parallel on those cores.

The crucial effect: **that one frame is now consuming resources in a 0.9 GB/core ratio** — wildly core-heavy. It absorbs the imbalance the previous memory-heavy frames created. When it finishes, it returns 9 cores + 8 GB, and the host is back near its natural 4 GB/core ratio. Future bookings start from a balanced state instead of a stranded one.

## Why this helps the host

- The 8 stranded cores **actually run code** instead of idling. Effective host utilization goes from ~50% to ~100% for the duration of that frame.
- Future bookings on the host don't re-strand because the ratio has been restored.

## Why this helps the farm

- **Throughput**: those 8 cores are now contributing render work. Multiply across thousands of hosts and a busy farm with chronically memory-heavy shows recovers a meaningful chunk of capacity.
- **Faster job completion**: the recipient layer is threadable, so 9× parallelism makes that frame finish ~9× faster (modulo Amdahl). The job's overall wallclock drops.
- **Scheduler honesty**: stranded cores show up in `host.idleCores` but are unbookable. Without recovery, the scheduler keeps "trying" this host on every report and getting rejected — wasted dispatch cycles. Recovery either uses the cores or clears the marker after 5 s, so the scheduler's view of capacity matches reality.
- **No global coordination required**: the fix is purely local to the host that completed a frame. No farm-wide repacking, no preemption, no migration. The cost is one extra field on `DispatchHost` and a check in `FrameCompleteHandler`.

## Why "give to one frame" specifically

You might expect "give the stranded cores to the next *several* frames." But that would just split the same problem across multiple frames — each would still book its own memory, and you'd re-strand. Giving **all the stranded cores to one threadable frame** concentrates the imbalance into a single booking that consumes lots of cores per GB. That single frame is the "balancer." Then `break` exits the dispatch loop (`CoreUnitDispatcher.java:300-302`) — the debt is paid, the host returns to normal scheduling on the next report.

It's basically a one-shot rebalancing trick: let a memory-heavy workload drift the host into a bad ratio, then use one fat threadable booking to drift it back.
