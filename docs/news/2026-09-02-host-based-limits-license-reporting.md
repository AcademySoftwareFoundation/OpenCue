---
layout: default
title: "September 2, 2026: Host-Based Limits and License Reporting"
parent: News
nav_order: 0
---

# Host-Based Limits and License Reporting

### Counting licenses the way license servers actually issue them, and packing the farm onto fewer machines

#### September 2, 2026

---

OpenCue limits now understand **licenses**, not just running frames. A limit can count one token per
*machine* rather than per frame, accept the license server's own view of who holds what, learn which
layers need a license by watching frames fail, and choose between blocking a booking and merely
biasing one.

Together these turn the limit system from a frame counter into something a studio can point at a
real Houdini, Katana or Mari pool.

## The Challenge

OpenCue counted one token per running frame. Two things were wrong with that for license management.

**Licensing is usually per host, not per frame.** Houdini/`sesinetd`, Katana, Mari and Clarisse all
issue per-machine licenses: any number of processes on one machine draw a single token. A limit of
`50` against a 50-seat Houdini pool stalled the farm at roughly 50 *frames* while the license server
still had 40+ free seats.

**Cuebot was not the only consumer.** Artists on workstations draw from the same pool. Cuebot had no
way to learn about them, so any internally-derived count was structurally wrong the moment a human
opened Houdini — and that is the case that matters most, because every license the farm takes is one
an artist can't have.

Underneath both was a subtler problem: **a cap is not really the goal**. When the pool is shared with
people, what you want is not "stay under 50" but "use as few machines as you can get away with". A
system that only knows how to say no cannot express that.

## The Solution

### A limit declares how it counts

`FRAME` is the old behavior and stays the default. `HOST` counts one token per distinct machine —
all frames on a host share it.

For a `HOST` limit, the maximum means something different, and it is worth saying plainly: it is
**the maximum number of machines the farm may spread this license across**. A studio with a 50-seat
Houdini pool that wants 20 seats kept free for artists sets the limit to 30, and the farm packs into
30 machines. That reframing is the primary footprint control, and CueGUI says it in those words.

### The license server gets a voice

An external reporter can push the license server's per-host view into Cuebot through a new
`ReportUsage` RPC. `samples/licensing/` ships a reference implementation for SideFX `sesinetd`, plus
a systemd timer and the config to map product strings to limit names.

The interesting part is how the two numbers merge. The obvious answer — take the larger — is wrong.
A Houdini frame checks a license out for hip load and scene build and releases it well before the
frame finishes, so counting every running frame as a held license permanently over-counts, and
`max()` guarantees the server's smaller, *true* number always loses.

Instead the two sources are treated as covering **disjoint time ranges**:

- **Settled** — what the server reported, as of the moment it was captured. Ground truth. Already
  reflects releases, artists, everything.
- **Pending** — frames booked since, which the server has not yet had a chance to observe.

They add, without double counting. A frame that has released its license drops to zero the moment
the server says so — which under the old model it never could.

CueGUI shows the split, because it tells an operator something a single number cannot: a
persistently high **Pending** means the reporter is behind, not that the farm is busy.

### The farm packs instead of spreading

Two mechanisms concentrate licensed work onto as few machines as possible, well before any threshold
is in sight.

**Layer ordering bias.** OpenCue dispatch is host-driven — a host reports in and Cuebot picks its
work. When a host already holds a license, layers needing that license are offered first. Read it as
*work this host can do without acquiring a new license comes first*. Layers with no license limits
are never penalized: they tie for first place.

**A soft spread threshold.** Below it, any host may take the work. At or above it, only hosts already
holding a token — the farm packs rather than spreading. Setting it to zero gives "never light up a new
machine for this license", a useful emergency lever when the report shows artists are starved.

A host that already holds a token can always book, even at the maximum. Its frames share the token,
so the booking consumes nothing new. That is the core new behavior, and it is what makes the maximum
read as *machines*.

### Advisory mode

A limit is now `ENFORCED`, `ADVISORY` or `DISABLED`.

**`ADVISORY` is the mode this feature was really missing.** The license server already enforces —
authoritatively, and for artists as well as the farm. So a site can let Cuebot never block a frame,
let genuine shortages surface as license-shortage exit statuses handled by the existing
[layer backoff](/news/2026-08-07-layer-start-after-deferred-booking/), and *still* get the whole
packing benefit, because the ordering bias is independent of the gate. For a farm whose licensing is
genuinely enforced upstream, that is the recommended configuration.

`DISABLED` lets an operator neutralize a misbehaving limit without deleting it — deleting a limit
throws away its layer bindings, which nobody can reconstruct from memory at 2am.

And a limit whose report has gone stale **stops enforcing and behaves as advisory**. The license
server is still enforcing for real, so gating the farm on data we know is wrong buys nothing and
costs idle time. A dead reporter is loud in the GUI and in metrics rather than quietly strangling
the farm.

### The farm learns which layers need a license

All of the above assumes layers are tagged with the limits they need — that submitters declare
`<limits>houdini</limits>`. In practice that coverage is poor, and a limit only constrains what is
tagged. An untagged Houdini layer burns real licenses while contributing nothing to the count.

Waiting for every submitter to tag correctly is not a plan. But the failures themselves are the
signal: a frame that exits with the license-shortage status has *proved* it needs that license.

So a limit can now claim an exit status, and a frame failing with it binds its layer to that limit on
the spot. Each failure becomes permanent coverage instead of a repeated stall. Bindings record where
they came from — declared in the spec, inferred from a failure, or added by an operator — so an
inferred binding is visible as such, discovery rate is measurable, and a mis-set exit status is
reversible in one action that never touches spec-declared bindings.

The exit status, the backoff and the auto-tagging are three separate settings because the
combinations are all useful. Backoff with no tagging is exactly the old behavior. **Tagging with no
backoff is pure discovery: learn coverage without changing dispatch at all** — the safest possible
way to start.

This also moves the old `dispatcher.layer_delay.rules` property onto the limit, where the exit status
finally names *which* license was short. As a side effect the rules become live-editable: changing a
backoff no longer needs a Cuebot restart.

### Roll it out in the order that can't hurt you

There is one interaction worth understanding before enabling anything, because it dictates the order.

As discovery improves coverage, more running frames count toward the limit — so **measured usage rises
even though actual license consumption has not changed**. On an enforced limit that looks like sudden
saturation and the farm stops booking, punishing the site for improving its own data.

So:

1. Create the limit **advisory**, with auto-tagging on. Nothing is gated. Packing starts immediately.
2. Watch the auto-bound layer count plateau. That is coverage converging.
3. Compare the settled usage against the license server's own numbers. When they track, the model is
   working.
4. *Then* consider enforcing — and quite possibly decide it adds nothing, since the license server
   enforces anyway.

Every step is observable and reversible, and stopping permanently at step 3 is a legitimate outcome.

## Monitoring

| Metric | Meaning |
| --- | --- |
| `cuebot_limit_auto_tag_total{limit}` | Layers auto-bound after a license failure — discovery rate |
| `cuebot_limit_delays_total{limit,exit_status}` | Automatic layer backoffs written |
| `cue_limit_bound_layers{limit,source}` | Coverage, split spec vs. auto |
| `cue_limit_usage{limit,kind}` | Usage, split settled vs. pending |
| `cue_limit_report_stale{limit}` | 1 when the external report has aged out |

Alert on `cue_limit_report_stale` sustained at 1 — that is a dead reporter, and the limit has stopped
blocking. Watch the auto-bound count for the opposite two signals: a plateau means coverage has
converged, while thousands per hour means a mis-set exit status.

## In CueGUI

The Limits plugin gained the type, mode, thresholds, the three-way usage split, holder and coverage
counts, report age and source, and the failure rule. Stale limits read `Advisory (stale)` and the
report age turns red, so nobody has to work out from three columns whether a limit is actually
gating.

Two new dialogs answer the two different questions people ask. **License Holders** answers "who is
using this license" — every host holding a token, Cue frames and artist workstations alike, with a
footer that states the arithmetic plainly. **Tagged Layers** answers "what does Cue think needs it",
grouped by service so a candidate for a permanent default becomes obvious.

The host monitor gained a **Licenses** column showing what each host holds, with externally-held
licenses parenthesized so an artist session on a render host is visible — and a `license:houdini`
filter to go with it.

## Availability

Available now in Cuebot, pycue and CueGUI, with a reference license reporter in
`samples/licensing/`. `rest_gateway` exposes the new RPCs automatically when rebuilt against the
proto.

Existing limits are unaffected: they migrate to per-frame counting and enforced mode, with no
reporter, and behave exactly as they did before. One upgrade note — the migration adds the name
uniqueness constraint `limit_record` never had, and will fail loudly on a database with duplicate
limit names. Precheck with:

```sql
SELECT str_name, COUNT(*) FROM limit_record GROUP BY str_name HAVING COUNT(*) > 1;
```

Full technical details, including the counting model, schema, configuration and rollout phases, are
in the [Licenses and Limits developer guide](/docs/developer-guide/licenses-and-limits/).
