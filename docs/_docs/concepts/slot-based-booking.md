---
title: "Slot-Based Booking"
nav_order: 21
parent: Concepts
layout: default
linkTitle: "Slot-Based Booking"
date: 2026-02-03
description: >
  Limit per-host concurrency by slots instead of cores and memory.
---

# Slot-Based Booking

### Limit per-host concurrency by slots instead of cores and memory

---

Slot-based booking is an alternative scheduling mode that uses "slots" as the unit of capacity on a host. Instead of matching frames to available cores and memory, OpenCue can match frames to available slots when a layer requests them and a host is configured with a slot limit.

## When to use slot-based booking

- License-limited tools where you want a hard cap on concurrent frames per host
- I/O heavy tasks that should run fewer frames than the core count suggests
- Mixed hardware pools where cores and memory are not the best proxy for capacity

## How it works

- Hosts can define a `concurrent_slots_limit`. A positive value enables slot-based booking on that host.
- Layers can define `slots_required` per frame. A positive value marks the layer as slot-based.
- When a host has a slot limit, it only accepts layers with `slots_required > 0`. Core, memory, and GPU booking are disabled on that host.
- When a layer requests slots, the scheduler matches frames based on available slots. Use tags, services, and limits to constrain hardware or license requirements.

> **Important**
> {: .callout .callout-warning}
> Setting a slot limit on a host changes how it is booked. The host will reject layers that do not set `slots_required`.

## Configure hosts (concurrent slots limit)

### CueCommander (CueGUI)

1. Open **CueCommander** and go to **Monitor Hosts**.
1. Select one or more hosts.
1. Right-click and choose **Update Slot Limit...**.
1. Enter a value for the maximum concurrent slots.

`0` disables slot-based booking for the host. A positive value enables slot-based booking and sets the maximum slots that can run concurrently.

### PyCue

```python
import opencue

host = opencue.api.findHost("rendernode01")
host.setConcurrentSlotsLimit(8)
```

## Configure layers (slots required)

### CueGUI layer dialog

1. Open a layer's properties dialog.
1. Set **Slots Required**.

`0` or a negative value means the layer is not slot-based. A positive value requests that many slots per frame.

### PyOutline

```python
import outline
import outline.modules.shell

layer = outline.modules.shell.Shell(
    "render",
    command=["render", "-f", "#IFRAME#"],
    range="1-100",
    slots_required=2,
)

# Or set it later:
layer.set_arg("slots_required", 2)
```

### PyCue (existing layer)

```python
import opencue

layer = opencue.api.findLayer("job_name", "render")
layer.setSlotsRequired(2)
```

### Job spec XML (CJS)

```xml
<layer name="render" type="Render">
  <cmd>render -f #IFRAME#</cmd>
  <range>1-100</range>
  <chunk>1</chunk>
  <slots_required>2</slots_required>
</layer>
```

The `slots_required` element is available in the CJS 1.16 DTD.

## Example: capacity math

If a host has `concurrent_slots_limit = 8` and a layer uses `slots_required = 2`, that host can run 4 frames from that layer at the same time.

## Operational notes

- Slot-based booking is per host. Only hosts with a positive slot limit enforce slots.
- Use tags, services, and limits to target the right hosts when using slots.
- Keep slot values small and consistent. `1` is the common default unless you need heavier weighting.
