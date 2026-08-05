---
title: "Configuring application licenses"
layout: default
parent: Other Guides
nav_order: 58
linkTitle: "Configuring application licenses"
date: 2026-08-04
description: >
  Gate booking of licensed layers on live seat counts from your license server
---

# Configuring application licenses

### Gate booking of licensed layers on live seat counts from your license server

---

This page describes how to configure live application licensing, which stops
Cuebot from booking frames that need an application license (Houdini Engine,
Katana, Maya, and so on) when the license server has no free seats.

A [Limit](/docs/other-guides/configuring-limits/) holds a static number an
admin typed, which works for an internal throttle but not for a real license
pool: the pool is also drawn on from outside the render farm — artist
workstations, CI, other farms. A fixed cap of 100 means nothing when 60 seats
are already checked out to people. The only authority on how many seats are
free is the license server itself, so Cuebot polls it and gates booking on the
live number.

## How it works

1. A layer declares the licenses it needs in its environment:

   ```xml
   <env>
       <key name="CUE_LICENSES">hengine,katana</key>
   </env>
   ```

   That declaration is the whole switch — there is deliberately no separate
   enable flag. A layer that declares nothing books exactly as before and pays
   nothing.

2. A background thread in every Cuebot polls
   `scheduler.license.provider` and keeps the latest sample in memory.

3. During booking, a frame whose layer declares licenses is only dispatched
   while every pool it lists has a free seat. The budget for each pool is
   `available - in-flight - headroom`, where *in-flight* counts the frames
   OpenCue booked after the sample was taken (the license server has not seen
   them yet) and *headroom* is seats deliberately left for interactive users.

4. Licensing **fails closed**. A layer that asks for a license is held — not
   run blind — when any of these are true:

   * no provider is configured,
   * no sample has arrived yet, or the sample is older than
     `scheduler.license.stale_seconds`,
   * the provider does not report the requested license at all,
   * the layer's declaration could not be read from the database.

   Holding licensed layers costs throughput on those layers only and recovers
   by itself; over-booking a pool would fail frames at checkout on the farm.

### Floating and host-based licenses

* A **floating** license consumes one seat per running frame.
* A **host-based** license (`"host_based": true` in the provider response)
  consumes one seat per machine, shared by every frame on that machine. Cuebot
  packs work onto machines that already hold the license: when a host report
  shows running frames holding host-based licenses, up to
  `scheduler.license.pack_jobs_max` pending jobs needing those licenses get
  the first shot at that host's idle resources, because an extra frame on a
  seated machine shares its one checkout while a fresh machine burns a seat.

## The license provider

Cuebot does not speak any vendor's license protocol. The site provides one
endpoint that reports every license the farm cares about, either over HTTP or
as a script wrapping the vendor CLI (`sesictrl`, `rlmutil`, `lmstat`, ...):

```
scheduler.license.provider=http://lic-reporter:9101/licenses
scheduler.license.provider=script:/site/bin/cue_licenses.sh
```

Both must return the same JSON:

```json
{"queried_at": 1690000000,
 "licenses": [{"name": "hengine", "feature": "Houdini Engine", "total": 800,
               "available": 794, "host_based": false,
               "hosts": [{"host": "wolf1018", "count": 1}]}]}
```

* `queried_at` (epoch seconds, when the numbers were true) is **required**. A
  response without it is rejected and the previous sample keeps aging toward
  stale, because a provider re-serving a cached payload would otherwise look
  fresh forever.
* `available` is server truth and must already net out every consumer,
  including OpenCue itself.
* `hosts` is optional. When present it enables seat counting for host-based
  licenses and reveals render nodes dual-used as workstations.

The provider string is displayed in the CueGUI **Licenses** view. Credentials
embedded in an `http(s)` URL (userinfo or query values) are redacted before
display, but a `script:` command line is shown as configured — keep secrets
out of it (read them from a file or the environment inside the script
instead).

## Configuration reference

All settings live in `opencue.properties` under `scheduler.license.*`:

| Property | Default | Description |
|----------|---------|-------------|
| `scheduler.license.provider` | (empty) | `http(s):` URL or `script:<cmd>` reporting license JSON. Empty disables polling; layers declaring licenses are then held. |
| `scheduler.license.poll_seconds` | `20` | Poll cadence. Every Cuebot polls, not just a leader, so a standby promoted by failover already holds a fresh sample. |
| `scheduler.license.timeout_seconds` | `10` | Hard deadline on one provider call; a hung vendor CLI is killed on it. |
| `scheduler.license.stale_seconds` | `300` | Age at which a sample stops being actionable and licensed layers are held. |
| `scheduler.license.inflight_pad_seconds` | `5` | Extra seconds added to the in-flight window, absorbing providers that stamp `queried_at` when collection finishes rather than starts. |
| `scheduler.license.headroom.default` | `0` | Seats withheld from the farm for every license without its own headroom. |
| `scheduler.license.headroom.<name>` | (default) | Per-license headroom, e.g. `scheduler.license.headroom.hengine=5`. |
| `scheduler.license.env_key` | `CUE_LICENSES` | Layer environment key that carries the license names. |
| `scheduler.license.denied_exit_statuses` | (empty) | Vendor exit codes meaning "could not get a license", e.g. `11,203`. |
| `scheduler.license.denied_requeue_limit` | `10` | How many times one frame may take the free license-denied requeue before ordinary retry accounting resumes. |
| `scheduler.license.pack_jobs_max` | `5` | Pending jobs offered a host already holding a host-based license, per host report. `0` disables packing. |

### License-denied exit statuses

Even with the gate, an artist can grab the last seat between the sample and
the real checkout on the render node. When the application then exits with a
status listed in `scheduler.license.denied_exit_statuses`, the frame is
requeued WAITING without spending a retry: the seat was a contended resource,
not a broken frame. `scheduler.license.denied_requeue_limit` bounds that free
requeue per frame, so a frame that is denied over and over (wrong feature
name, broken license setup on the application side) falls back to ordinary
retry accounting instead of bouncing forever.

## Deployment notes

* Migration `V46` adds the index `i_layer_env_str_key` on
  `layer_env (str_key, pk_layer)`, which every licensing query drives from. A
  plain `CREATE INDEX` briefly write-locks `layer_env`; on large installs
  pre-create it with `CREATE INDEX CONCURRENTLY` before upgrading, or migrate
  in a quiet window.
* No new services or leaders: every Cuebot polls the provider independently,
  and the in-flight correction is derived from the shared database, so every
  Cuebot computes the same budgets.

## Monitoring

* In CueGUI, load the read-only **Licenses** view from
  **Views/Plugins->Cuecommander** to see every license in the current sample,
  its seat counts, headroom and OpenCue's own usage, plus the poller status.
  See [Monitoring application licenses](/docs/user-guides/monitoring-licenses/).
* From Python:

  ```python
  import opencue
  status = opencue.api.getLicensingStatus()
  print(status.configured(), status.stale(), status.ageSeconds())
  for lic in status.licenses():
      print(lic.name(), lic.available(), "of", lic.total())
  ```

* Cuebot logs one throttled warning per minute while licensed layers are held
  (`LicenseSource: ... holding licensed layers`), and a loud one when layers
  declare licenses with no provider configured.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Licensed layers never book, everything else books | No provider configured, or the provider is down and the sample went stale — check the **Licenses** view status line. |
| A single layer never books | Its `CUE_LICENSES` names a license the provider does not report; the Licenses view shows exactly which pools exist. |
| Frames fail on the farm with a license error | Add the vendor's exit code to `scheduler.license.denied_exit_statuses` and consider raising that license's headroom. |
| Fewer frames book than seats appear free | Headroom plus the in-flight correction; see the Licenses view's Headroom and Cue Frames columns. |

## What's next?

* [Monitoring application licenses](/docs/user-guides/monitoring-licenses/)
* [Configuring limits](/docs/other-guides/configuring-limits/)
