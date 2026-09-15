"""LICENSE test: the external license reporter.

Cuebot never talks to a license server -- that is the whole point of the limits
design. Something outside the cue polls the server and feeds Cuebot the view via
``LimitInterface.ReportUsage``. This is that something: the sim's stand-in for a
site's ``sesictrl``-style reporter.

It bridges ``fake_license.py`` (the license server) to cuebot:

  1. ensures a ``limit_record`` exists per pool, typed the way the pool bills --
     ``HOST`` for a per-machine license (hengine), ``FRAME`` for a floating one
     (katana, maya);
  2. every ``SIM_LIC_POLL_S`` seconds posts each pool's holder snapshot, so
     cuebot's settled usage counts the seats artists hold OUTSIDE the farm, not
     just the frames inside it.

The report is a FULL snapshot per limit: cuebot replaces the hold set with what
it is given, so an empty list clears it. ``capture_time`` carries the server's
own ``queried_at``, which keeps the settlement watermark honest when this
reporter is slow -- frames booked after the snapshot are counted as pending
rather than vanishing into the gap.

Two pool shapes, because real license servers differ:

  hosts mode (default)
      The server enumerates holders. Each machine is reported with the tokens it
      holds: one per checkout for a floating pool, one per machine for a
      host-based one. Cuebot sees foreign holders directly.

  counts-only mode (``SIM_LIC_NO_HOSTS=1``, the Houdini/``sesictrl`` shape)
      The server exposes only totals. Blind to WHO holds what, the reporter
      cannot send a hold set at all, so it bounds the pool instead: it publishes
      ``available + what cuebot already uses`` as the pool size, which is the
      total minus everyone outside the cue. The farm is then capped by what is
      genuinely free rather than by the license total.

      Those two numbers are read from different clocks -- ``available`` is as of
      the server's last sample, cuebot's usage as of the last read -- and the
      farm moves in between. When usage falls across the gap the sum overstates
      the pool, and the farm books straight into the overstatement. No reporter
      can align the clocks, so this one publishes the SMALLEST estimate of the
      last ``SIM_LIC_COUNTS_WINDOW`` polls: a transient overshoot is filtered
      out, while a genuine increase survives once the whole window agrees. Erring
      small costs a little throughput; erring large fails frames at checkout. On
      top of that it keeps ``SIM_LIC_COUNTS_PAD`` seats in reserve for bookings
      made after the sample that are not yet visible anywhere.

      It resizes the pool with ``SetMaxValue`` and never calls ``ReportUsage``.
      Posting an empty hold set would be a lie in two ways: it asserts nobody
      holds the license, and it stamps a report watermark, which narrows cuebot's
      pending scan to the settle window and hides every proc booked before it. A
      never-reported limit instead counts EVERY running proc of a bound layer
      (see "Never-reported limits" in the licenses-and-limits guide), which is
      precisely the counting a reporter without holder data needs. Getting this
      wrong is not subtle: a HOST pool spreads over every machine whose booking
      has aged out of the window.

Katana is published `SIM_LIC_HEADROOM_KATANA` seats smaller than it really is.
Reserving seats for interactive users is a policy decision, and with the limit
design it belongs here rather than in cuebot: the reporter publishes the pool it
wants the farm to fit inside. That reserve is what lets an artist still get a
seat with the farm flat out, which the watcher asserts.

usage: license_reporter.py [duration_s]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "opencue_proto"))

import grpc  # noqa: E402

import farm_spec as spec  # noqa: E402
import limit_pb2  # noqa: E402
import limit_pb2_grpc  # noqa: E402

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
PORT = os.environ.get("SIM_LIC_PORT", "9101")
LIC_URL = f"http://127.0.0.1:{PORT}/licenses"
# Must stay above limit.min_report_interval_seconds or cuebot rate-limits us and
# the limit drifts stale (a stale limit stops blocking -- fail-open by design).
POLL_S = float(os.environ.get("SIM_LIC_POLL_S", "4"))
# Seats withheld from the published katana pool for interactive users.
HEADROOM_KATANA = int(os.environ.get("SIM_LIC_HEADROOM_KATANA", "8"))
# Seconds after which cuebot treats our reports as stale and stops gating.
REPORT_TTL = int(os.environ.get("SIM_LIC_REPORT_TTL", "60"))
NO_HOSTS = os.environ.get("SIM_LIC_NO_HOSTS", "0") == "1"
# The pool whose limit claims the "license denied" exit status, and the status
# itself. Only ONE limit may claim a status (partial unique index), so fake_rqd
# denies frames of this pool only.
#
# delay_minutes MUST be > 0. Cuebot requeues a denied frame for free only for a
# rule that carries a booking backoff (FrameCompleteHandler.isLimitDenied); a
# delay-0 rule is pure discovery -- it auto-tags the layer but leaves frame
# completion alone, so the denial would be charged as an ordinary failure. One
# minute is the smallest the column allows (the unit is minutes).
#
# auto_tag stays off so every binding in this test is provably SPEC.
DENY_POOL = os.environ.get("SIM_LIC_DENY_POOL", "katana")
DENY_STATUS = int(os.environ.get("SIM_LIC_DENY_STATUS", "203"))
DENY_DELAY_MIN = int(os.environ.get("SIM_LIC_DENY_DELAY_MIN", "1"))
# Polls the counts-only pool estimate is minimised over. Covers the skew between
# the server's sample and our last report.
COUNTS_WINDOW = int(os.environ.get("SIM_LIC_COUNTS_WINDOW", "3"))
# Seats held back in counts-only mode for bookings made after the server's sample
# and not yet visible anywhere. The window above filters transient overshoot but
# cannot cover a dispatch batch landing inside the skew, which is the same race
# the retired maestro.license.inflight_pad_seconds covered. A counts-only
# integration has to keep a reserve or it will occasionally overshoot.
COUNTS_PAD = int(os.environ.get("SIM_LIC_COUNTS_PAD", "4"))

# Recent counts-only pool estimates per limit, oldest first.
_recent = {}
SOURCE = os.environ.get("SIM_LIC_REPORT_SOURCE", "fake_license@sim")
PSQL = spec.psql_cmd()


def fetch():
    with urllib.request.urlopen(LIC_URL, timeout=10) as r:
        return json.load(r)


def ensure_limits(pools):
    """Create one limit_record per pool, typed for how the pool bills.

    Cuebot resolves a layer's <limit> by name, so the rows must exist before the
    injector launches. Written directly rather than over gRPC for the same
    reason inject_limit.py does: it is fixture setup, not the API under test.
    Re-created each run so a pool's type or size cannot survive from a prior one.
    """
    stmts = []
    for p in pools:
        name = p["name"].replace("'", "")
        kind = "HOST" if p.get("host_based") else "FRAME"
        # Only the denial pool carries a failure rule; the column is uniquely
        # indexed, so a second claimant would fail the insert.
        status = str(DENY_STATUS) if name == DENY_POOL else "NULL"
        stmts.append(
            f"DELETE FROM layer_limit WHERE pk_limit_record IN "
            f"(SELECT pk_limit_record FROM limit_record WHERE str_name='{name}');"
            f"DELETE FROM limit_record WHERE str_name='{name}';"
            f"INSERT INTO limit_record "
            f"(pk_limit_record, str_name, int_max_value, str_type, str_enforcement, "
            f"int_report_ttl, int_exit_status, int_delay_minutes, b_auto_tag) VALUES "
            f"(uuid_in(md5(random()::text || clock_timestamp()::text)::cstring), "
            f"'{name}', {int(p['total'])}, '{kind}', 'ENFORCED', {REPORT_TTL}, "
            f"{status}, {DENY_DELAY_MIN if name == DENY_POOL else 0}, false);")
    r = subprocess.run(PSQL + ["-c", "".join(stmts)], capture_output=True, text=True,
                       timeout=30)
    if r.returncode != 0:
        sys.exit(f"[reporter] could not create limits: {(r.stderr or r.stdout)[-500:]}")
    print(f"[reporter] denial rule: {DENY_POOL} claims exit status {DENY_STATUS} "
          f"(backoff {DENY_DELAY_MIN}m)", flush=True)
    print(f"[reporter] limits ready: "
          + ", ".join(f"{p['name']}({'HOST' if p.get('host_based') else 'FRAME'}"
                      f",max={p['total']})" for p in pools), flush=True)


def _headroom(name, total):
    """Seats withheld from a published pool for interactive users."""
    return max(0, total - HEADROOM_KATANA) if name == "katana" else total


def build_reports(payload):
    """One LimitReport per pool from the server's holder snapshot (hosts mode)."""
    captured = int(payload.get("queried_at") or 0)
    reports = []
    for p in payload.get("licenses", []):
        hosts = [limit_pb2.LimitHostUsage(host_name=h["host"], tokens=int(h["count"]))
                 for h in p.get("hosts", []) if int(h.get("count", 0)) > 0]
        reports.append(limit_pb2.LimitReport(
            limit_name=p["name"], hosts=hosts,
            total_licenses=_headroom(p["name"], int(p.get("total") or 0)),
            capture_time=captured))
    return reports


def pool_sizes(payload, usage):
    """Counts-only: the pool size to publish per limit.

    `usage` is what cuebot currently says it is using, which turns the server's
    `available` back into a pool size. See the module docstring for why this is
    minimised over a window and why it is applied with SetMaxValue.
    """
    sizes = {}
    for p in payload.get("licenses", []):
        name = p["name"]
        estimate = int(p.get("available") or 0) + int(usage.get(name, 0))
        window = _recent.setdefault(name, [])
        window.append(estimate)
        del window[:-COUNTS_WINDOW]
        sizes[name] = max(0, _headroom(name, min(window)) - COUNTS_PAD)
    return sizes


def main():
    deadline = time.time() + DURATION
    chan = grpc.insecure_channel(spec.GRPC)
    stub = limit_pb2_grpc.LimitInterfaceStub(chan)

    for _ in range(30):
        try:
            payload = fetch()
            break
        except Exception:
            time.sleep(1)
    else:
        sys.exit("[reporter] license server never answered")
    ensure_limits(payload.get("licenses", []))

    mode = ("counts-only: SetMaxValue, no hold snapshot" if NO_HOSTS
            else "holder snapshots via ReportUsage")
    print(f"[reporter] {mode} to {spec.GRPC} every {POLL_S}s "
          f"as '{SOURCE}' for {DURATION}s", flush=True)

    sent, skipped = 0, 0
    while time.time() < deadline:
        try:
            payload = fetch()
            if NO_HOSTS:
                # No holder data to post -- only resize the pools, leaving the
                # limits never-reported so their pending scan covers every
                # running proc. Usage is read fresh each round for the estimate.
                limits = list(stub.GetAll(limit_pb2.LimitGetAllRequest(), timeout=20).limits)
                usage = {lim.name: lim.current_usage for lim in limits}
                for name, size in pool_sizes(payload, usage).items():
                    stub.SetMaxValue(limit_pb2.LimitSetMaxValueRequest(
                        name=name, max_value=size), timeout=20)
                sent += 1
            else:
                resp = stub.ReportUsage(limit_pb2.LimitReportUsageRequest(
                    reports=build_reports(payload), source=SOURCE), timeout=20)
                limits = list(resp.limits)
                sent += 1
                skipped += len(resp.skipped_limits)
                if resp.unknown_limits:
                    print(f"[reporter] unknown limits: {list(resp.unknown_limits)}", flush=True)
            # Printed so a failed run shows what cuebot was acting on.
            if sent % 5 == 1:
                print("[reporter] " + "  ".join(
                    f"{lim.name} use={lim.current_usage}"
                    f"(settled={lim.settled_usage}+pending={lim.pending_usage})"
                    f"/max={lim.max_value}"
                    f"{' STALE' if lim.report_stale else ''}" for lim in limits),
                    flush=True)
        except Exception as e:
            print(f"[reporter] report failed: {e}", flush=True)
        time.sleep(POLL_S)
    print(f"[reporter] done: {sent} reports accepted, {skipped} limits skipped", flush=True)


if __name__ == "__main__":
    main()
