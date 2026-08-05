---
title: "Monitoring application licenses"
nav_order: 45
parent: User Guides
layout: default
linkTitle: "Monitoring application licenses"
date: 2026-08-04
description: >
  Inspect live application license pools and OpenCue's usage of them
---

# Monitoring application licenses

### Inspect live application license pools and OpenCue's usage of them

---

This guide describes the **Licenses** view in CueGUI, a read-only window into
the application licenses Cuebot polls from its license provider. Use it to
answer "why is my licensed layer not booking?" and "how much of each pool is
the farm holding?" without shelling into Cuebot.

The view is read-only by design: the seat counts belong to the license server,
and the tuning (provider endpoint, headroom, poll cadence) lives in Cuebot's
`opencue.properties`. See
[Configuring application licenses](/docs/other-guides/configuring-application-licenses/)
for the setup.

## Opening the view

1. Open CueGUI.

1. Load the **Licenses** view from the **Views/Plugins->Cuecommander** menu.

## The status line

The line above the table reports the poller itself:

* **Provider ... — sample Ns old (stale after Ms), poll every Ps** — healthy.
  The sample age includes how old the provider said its numbers were when it
  answered.
* **STALE — licensed layers are held. ...** — the sample aged past
  `scheduler.license.stale_seconds` (provider down or unreachable). Booking of
  licensed layers has stopped until a fresh sample lands.
* **Waiting for the first sample from ...** — Cuebot restarted recently or the
  provider has not answered yet.
* **License provider not configured ...** — `scheduler.license.provider` is
  unset on Cuebot; any layer declaring licenses is held.

## Columns

| Column | Meaning |
|--------|---------|
| License | Pool name as layers declare it in `CUE_LICENSES`, e.g. `hengine`. |
| Feature | Human-readable name from the provider, e.g. `Houdini Engine`. |
| Type | `Floating` (one seat per frame) or `Host-based` (one seat per machine, shared by all frames on it). |
| Total | Seats the license server owns. |
| Available | Seats the server reports free, net of every consumer — workstations, CI and other farms included. |
| In Use | Seats checked out anywhere (Total minus Available). |
| Headroom | Seats withheld from the farm for interactive users (`scheduler.license.headroom.<name>`). |
| Cue Frames | Frames currently running on this OpenCue deploy whose layer declares the license. |
| Cue Hosts | Distinct hosts running those frames. |
| Provider Hosts | Hosts the license server reports holding a seat (any consumer); 0 when the provider does not report hosts. |

The table refreshes every 60 seconds; **Refresh** forces it.

## Reading the numbers

* A licensed layer books only while `Available - Headroom` leaves room for it
  (Cuebot also subtracts the frames it booked since the sample was taken).
* For a host-based license, an extra frame on a host that already holds the
  license is free; only fresh machines consume seats.
* A license your layer declares that does **not** appear in the table is a
  held layer: the provider does not report that pool, so Cuebot refuses to
  book it blind. Fix the layer's `CUE_LICENSES` or the provider's report.

## What's next?

* [Configuring application licenses](/docs/other-guides/configuring-application-licenses/)
