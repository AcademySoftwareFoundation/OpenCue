---
layout: default
title: "August 7, 2026: Deferred Layer Booking with Start After"
parent: News
nav_order: 1
---

# Deferred Layer Booking with Start After

### Automatic license-shortage backoff and operator-scheduled layer starts

#### August 7, 2026

---

Layers can now carry a **start-after time**: a timestamp meaning "do not book frames of this layer
before this time." Two writers use it:

1. **Automatic backoff.** When a frame reports an operator-configured exit status — such as the
   license shortage that RQD's [log-based exit-status rules](/news/2026-08-06-rqd-log-exit-status-rules/)
   can detect — Cuebot pushes the whole layer's start-after time a few minutes into the future
   instead of letting the frames retry immediately or die. Frames retry indefinitely without ever
   consuming a retry.
2. **Operators and tools**, via a new `SetStartAfter` RPC, a CueGUI *Set Start After…* right-click
   action, and pycue's `Layer.setStartAfter()` — which also delivers a general-purpose "start this
   layer at 18:00" capability.

## The Challenge

A license shortage is not a property of the frame that hit it. Previously Cuebot could not tell one
from a generic crash, so a farm at license cap produced a wave of dead frames that someone had to
clean up by hand, every single time. Retrying immediately is pointless — the license is still gone —
and `maxRetries` is typically low enough that the frames died within seconds of each other.

RQD's log-based exit-status rules gave RQD the ability to recognise the failure from the frame log
and report a substitute exit status. This feature is the Cuebot half: react to that status by
pausing the *layer* for a few minutes rather than killing its frames. Pausing the layer is correct
because every frame in a layer depends on the same license — one failure is enough to establish
that the pool is exhausted.

## The Solution

### Automatic backoff configuration

Add matching configuration to both sides:

`rqd.yaml` (see the [Rust RQD reference](/docs/reference/rust-rqd/)):

```yaml
runner:
  log_exit_status_rules:
    - name: "HOUDINI_LICENSE_ERROR"
      regex: "A usable license to run the application is installed but they are all in use"
      exit_status: 330
```

`opencue.properties`:

```properties
# Comma-separated exit_status:minutes pairs. Empty (default) disables the feature.
dispatcher.layer_delay.rules=330:5
```

When a frame exits `330`, Cuebot marks the frame `WAITING` (no retry consumed), records
`Automatic backoff: exit status 330` on the layer, and defers the layer's booking for 5 minutes.
In-flight frames on the same layer reporting the same status collapse into that one write. When the
delay expires the layer books again; if the license is still gone, the next report re-delays it.
`330` is the conventional license-shortage code — it sits safely outside the exit statuses Cuebot
reserves internally.

Key behaviors:

- **Off by default** — an empty rule list changes nothing on upgrade.
- **No retries consumed** — configured statuses are excluded from retry counting, so frames keep
  their full retry budget for genuine failures.
- **Auto-eat wins** — on a job with auto-eat enabled a matching failure is still eaten, so the job
  finishes promptly.
- **Operator intent survives** — the automatic write only ever moves the time later; an
  operator-set 18:00 start cannot be pulled earlier by a backoff, and a longer rule can extend a
  shorter active delay.
- **Both dispatchers honour the gate** — the Cuebot dispatcher (including local dispatch) and the
  Rust scheduler both enforce it at the frame-reservation update, the single authoritative choke
  point.

### Operator scheduling

In CueGUI's layer view, right-click → *Set Start After…* opens a picker with quick presets
(+15m, +1h, +4h, Tonight 18:00). Delayed layers show a tinted row and a *Start After* column whose
tooltip explains why the layer is delayed — `Automatic backoff: exit status 330` or
`Set by <user>`. *Clear* makes the layer bookable immediately (though it may be re-delayed
automatically while the underlying condition persists).

CueWeb offers the same thing: the Layers table gained a sortable *Start After* column with the
reason on hover, delayed rows are tinted, and the layer right-click menu (in the table and on layer
nodes in the Job Dependency Graph) has a *Set Start After…* dialog carrying the same presets and
*Clear*. The picker shows local time and sends UTC epoch seconds.

From python:

```python
layer.setStartAfter(epoch_seconds)   # defer booking
layer.startAfter()                   # read it back (0 = not set)
layer.startAfterReason()             # provenance, displayed verbatim
layer.clearStartAfter()              # bookable immediately
```

### Monitoring

Two Prometheus metrics make a broken license server loud instead of silent:

| Metric | Meaning |
| --- | --- |
| `cuebot_layer_delays_total{exit_status}` | Automatic delays written, by exit status |
| `cuebot_layers_delayed` | Layers currently gated |

A layer stuck re-delaying for hours shows as a flat non-zero gauge with a climbing counter — alert
on `cuebot_layers_delayed > 0` sustained.

## Availability

The layer start-after gate is available now in Cuebot, the Rust scheduler, pycue, CueGUI, and
CueWeb. `rest_gateway` exposes `SetStartAfter` as `POST /job.LayerInterface/SetStartAfter` with no
extra registration — it generates a route per RPC from `job.proto`, so the endpoint appears when
the gateway is rebuilt against this proto.
