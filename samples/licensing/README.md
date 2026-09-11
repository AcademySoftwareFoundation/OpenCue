# License reporting for OpenCue limits

`sesictrl_report.py` polls a SideFX `sesinetd` license server via `sesictrl` and
pushes its per-host view of checkouts into Cuebot limits, using the
`LimitInterface.ReportUsage` RPC. That closes the two gaps Cuebot cannot see on
its own:

- **Per-host licensing.** Houdini licenses are held per machine: any number of
  frames on one host draw a single license. A limit of type `HOST` counts that
  way, and its maximum is the number of *machines* the farm may spread across.
- **Non-Cue consumers.** Artists on workstations draw from the same pool. The
  report includes them, so the farm's accounting reflects reality.

## Setup

1. Create the limits the config names, as `HOST` type. Start them `ADVISORY`
   with a failure rule so coverage grows from failures while nothing is gated:

   ```python
   import opencue
   from opencue_proto import limit_pb2

   opencue.api.createLimit('houdini', 30,
                           limitType=limit_pb2.HOST,
                           enforcement=limit_pb2.ADVISORY,
                           exitStatus=330, delayMinutes=2)
   ```

   Use the exit status your RQD emits for license failures via
   `rqd.yaml runner.log_exit_status_rules` (330 by convention).

2. Copy `sesictrl_limits.yaml` to `/etc/opencue/` and map your `sesictrl`
   product strings to the limit names.

3. Validate the parser against a captured sample before going live — SideFX
   does not publish the JSON schema and it varies between Houdini versions:

   ```sh
   sesictrl print-license --format json --show-all > /tmp/sesi.json
   ./sesictrl_report.py --config /etc/opencue/sesictrl_limits.yaml \
       --from-file /tmp/sesi.json --dry-run -vv
   ```

   If nothing parses, adapt the single function `parse_sesictrl_json()`.

## Running

### cron

```cron
* * * * * /usr/bin/flock -n /var/lock/sesictrl_report.lock \
    /opt/opencue/samples/licensing/sesictrl_report.py \
    --config /etc/opencue/sesictrl_limits.yaml \
    >> /var/log/opencue/sesictrl_report.log 2>&1
```

`flock` matters: overlapping runs posting different snapshots would flap the
dispatch gate.

### systemd timer (preferred)

A timer gives real logging, a restart policy, no `flock` (with `Type=oneshot`),
and can poll faster than cron's one-minute floor:

```ini
# /etc/systemd/system/sesictrl-report.service
[Unit]
Description=Report sesinetd license usage to Cuebot

[Service]
Type=oneshot
ExecStart=/opt/opencue/samples/licensing/sesictrl_report.py \
    --config /etc/opencue/sesictrl_limits.yaml -v
```

```ini
# /etc/systemd/system/sesictrl-report.timer
[Unit]
Description=Poll sesinetd every 30 seconds

[Timer]
OnBootSec=60
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
```

## Tuning

- Keep Cuebot's `limit.settle_window_seconds` at roughly **twice the poll
  interval**, and each limit's report TTL comfortably above it so a brief
  outage does not flap the stale flag.
- The script deliberately **posts nothing on any failure** (sesictrl error,
  parse error). An empty report would clear every hold and open the gate wide;
  going quiet instead lets Cuebot's staleness handling degrade the limit to
  advisory, which is the designed response.
- A limit listed in the response's `skipped_limits` means another reporter
  posted within Cuebot's `limit.min_report_interval_seconds`. Losing that race
  is normal: every other limit in the batch still applied, and the script logs
  the skip and exits zero.
