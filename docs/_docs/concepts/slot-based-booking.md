---
title: "Slot-Based Booking"
nav_order: 14
parent: Concepts
layout: default
linkTitle: "Slot-Based Booking"
date: 2026-07-03
description: >
  Booking frames by concurrency slots instead of cores and memory
---

# Slot-Based Booking

Slot-based booking is an alternative dispatch mode for pipelines whose frames are
limited not by CPU or memory but by some other shared resource — storage bandwidth,
network throughput, a licensed external service, etc. In these pipelines what matters
is bounding *concurrency*, not resource consumption.

A slot-based frame ignores cores and memory entirely: it reserves **0 cores and 0
memory** and runs unpinned on the host. The only thing that limits it is a **slot
budget**.

> **Note:** Slot-based booking is implemented in the standalone Rust scheduler. Cuebot
> does not make slot-based booking decisions; it stores the configuration and publishes
> slot release/limit deltas to the scheduler.

## The two slot axes

Slot booking is governed by two independent limits:

1. **Per-host cap** — `host.concurrent_slots_limit`. A host with this set is a
   *slot host*: it runs **only** slot-based layers, up to this many concurrent slots.
2. **Per-hierarchy max** — a `max_slots` limit at the **subscription**, **folder**, and
   **job** levels, enforced by the scheduler's accounting store, parallel to (and
   independent of) the cores/GPUs limits.

Both must be satisfied for a slot frame to book.

## Strict pairing

Slot hosts and slot layers are strictly paired:

| Host \ Layer | Regular layer | Slot layer (`slots_required > 0`) |
|---|---|---|
| **Regular host** | books by cores/memory | **rejected** |
| **Slot host** (`concurrent_slots_limit ≥ 0`) | **rejected** | books by slots |

A slot host never runs a regular layer, and a slot layer never runs on a regular host.

## Limit values

Every `max_slots` limit uses the convention:

- **`-1`** — unlimited (the migration default; a slot layer is bounded only by host
  capacity until an admin sets a limit).
- **`0`** — reject all slot work at this level.
- **`N`** — cap at N concurrent slots.

An unseeded limit is treated as `0` (reject-all) — the scheduler **fails closed** on the
slot axis: a seeding bug manifests as "slot work won't book," never as overrunning a hard
cap. Regular (cores/memory) layers are unaffected by `max_slots`, and slot layers are
unaffected by the cores/GPUs limits.

## Making a layer slot-based

Set `slots_required` on the layer in the job spec (spec version **1.16**+). With
PyOutline:

```python
layer = outline.modules.shell.Shell(
    "bandwidth_bound_layer",
    command=["my_command"],
    slots_required=1,   # each frame consumes one slot
)
```

A frame may require more than one slot (`slots_required > 1`) — a "heavy" frame counts
N against the host cap and all three hierarchy limits. Slot-based layers are forced
non-threadable.

## Configuring the limits

- **Host slot cap** — set a host's concurrent slots limit from CueCommander, or via
  PyCue: `host.setConcurrentSlotsLimit(8)` (`-1` disables slot mode).
- **Subscription / folder / job max slots** — set from the GUI or via PyCue
  (`subscription.setMaxSlots(...)`, `group.setMaxSlots(...)`, `job.setMaxSlots(...)`),
  mirroring how `max_cores` is managed.

## How it accounts

`proc.int_slots_reserved` is the single source of truth for slot usage. Per-host slot
counts and per-subscription/folder/job counts both derive from `SUM(proc.int_slots_reserved)`,
so RQD does not need to report slots. The scheduler's periodic recompute reconciles the
slot counters from that sum, the same way it reconciles cores/GPUs — a dropped release
leaves a counter reading high (under-book), healed by the next recompute.
