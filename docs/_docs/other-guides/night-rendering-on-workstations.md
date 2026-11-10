---
title: "Night rendering on workstations"
nav_order: 150
parent: Other Guides
layout: default
linkTitle: "Night rendering on workstations"
date: 2026-11-09
description: >
  Open artist workstations for rendering overnight and clear them before the morning
---

# Night rendering on workstations

### Open artist workstations for rendering overnight and clear them before the morning

---

Workstations with nimby enabled can render overnight and be empty by the time artists sit down.
Two scheduled `cueadmin` calls do it:

- **Evening:** unlock the workstations so Cuebot books frames on them.
- **Morning:** lock them and kill their running frames.

Killed frames go back to waiting without spending a retry, so a job that is interrupted every
morning doesn't slowly turn into dead frames. This is best effort: if a killed frame's completion
report reaches Cuebot first, the frame is judged like any other failure and can spend a retry, or
go dead if it has none left or ran longer than 12 hours. Nimby keeps working as usual: if an artist comes
back during the night, their activity still locks the host and kills its frames.

## Before you start

- Install `cueadmin` on a machine that can reach Cuebot (see
  [Installing CueAdmin](/docs/getting-started/installing-cueadmin)).
- Make sure the workstations report nimby as enabled. `cueadmin -lh -nimby` lists them.
- Shows need a subscription to the workstations' allocation to render on them (see
  [Desktop rendering control](/docs/other-guides/desktop-rendering-control)).

## Schedule the lock and unlock

Pick a source tag for the schedule, for example `night-render`, and add two cron entries:

```
# Weekdays: open workstations at 20:00, clear them at 07:00
0 20 * * 1-5  cueadmin -unlock -nimby -source night-render -force
0  7 * * 1-5  cueadmin -lock -nimby -kill-frames -source night-render -force
```

`-force` skips the confirmation prompt, which a cron job can't answer. The evening unlock only
releases hosts locked with the `night-render` tag, so a workstation locked earlier by hand stays
locked until it's unlocked by hand (`cueadmin -host ws-01 -unlock`).

To give long frames a chance to finish, lock first and kill later:

```
30 6 * * 1-5  cueadmin -lock -nimby -source night-render -force
0  7 * * 1-5  cueadmin -lock -nimby -kill-frames -source night-render -force
```

The first call stops new frames from being booked; the second kills whatever is still running.
Locking again with the same source is safe.

## How other locks are treated

The schedule never takes over or lifts someone else's lock:

- A host locked by another source, for example a maintenance lock taken with
  `cueadmin -host ws-01 -lock`, is skipped by both calls and stays locked.
- A host nimby-locked because an artist is working is locked by the morning call, and isn't
  touched by the evening call.

A host that is maintenance-locked overnight and unlocked in the morning misses the morning lock.
It's picked up by the next scheduled run.

## Reading the output

Each run prints a summary, which cron mails to the job owner by default:

```
Locked: 42, unreachable: 1, skipped: 3, frames killed: 17
Unreachable hosts: ws-118
Frames whose kill could not be confirmed (still running):
  0042-comp
```

- **Unreachable:** Cuebot locked the host, so nothing new is booked on it, but RQD didn't answer.
  Check that the machine is up.
- **Skipped:** the host is locked by another source.
- **Frames whose kill could not be confirmed:** these keep running until their host reports them
  done. They may spend a retry.

## From Python

The same calls are available in pycue:

```python
import opencue

result = opencue.api.lockHosts("night-render", kill=True, nimby=True)
print(len(result.locked), result.framesKilled, result.framesDeferred)

opencue.api.unlockHosts("night-render", nimby=True)
```

Both take the usual host search options (`host=[...]`, `match=[...]`, `alloc=[...]`, and so on)
and refuse a request with no filter at all, so an empty call can't lock the whole farm.

## Related documentation

* [CueAdmin reference](/docs/reference/tools/cueadmin) - Bulk lock flags
* [Desktop rendering control](/docs/other-guides/desktop-rendering-control) - Allocations and subscriptions for workstations
* [NIMBY concept guide](/docs/concepts/nimby) - How nimby locks a host
