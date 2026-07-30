"""Fake license server for the LICENSE scenario: hengine, katana and maya.

Stands in for a real floating-license server (SESI/RLM/FlexLM behind a site
exporter) and serves cuebot's provider contract on
``http://127.0.0.1:9101/licenses``:

    {"queried_at": <epoch s>,
     "licenses": [{"name": "katana", "feature": "Katana", "total": 120,
                   "available": 97, "host_based": false,
                   "hosts": [{"host": "jaime0007", "count": 1}]}]}

The point of the whole exercise is that ``available`` is NOT a number cuebot
controls. A real server counts every consumer, so this one does too:

    available = total - (frames the farm is running) - (seats artists hold)

The farm's share is read straight from Postgres (RUNNING frames whose layer
declares the license in CUE_LICENSES), which is the same reality RQD is
enacting. That closed loop is what makes the scenario a real test: if the
planner over-books, this server's next sample shows it, and the watcher sees the
pool oversubscribed.

It is also deliberately BEHIND. It re-reads the farm only every
``SIM_LIC_SAMPLE_S`` seconds and stamps ``queried_at`` with the time of that
read, so cuebot is always acting on stale numbers and must correct with its own
in-flight term -- exactly the race a real deployment has.

Three licenses, each covering a different case:

  hengine  host-based (host_based=true): the cap counts distinct MACHINES, and
           every frame on a seated machine shares its one checkout. Two seats
           are held from the start by artist workstations outside the cue, so
           the farm has to see foreign holders and work around them.
  katana   floating with HEADROOM configured on the cuebot side. Artists grab
           seats mid-run; because cuebot holds seats back, they SUCCEED even
           though the farm is saturated. That is the feature's whole purpose,
           and the watcher asserts it.
  maya     floating, no headroom, no artist activity: the plain "never exceed
           the pool" case.

Endpoints
  /licenses  the provider contract cuebot polls.
  /state     ground truth for the watcher (totals, artist holds, farm usage),
             so the verdict does not have to reimplement any of this.

usage: fake_license.py [duration_s]
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
PORT = int(os.environ.get("SIM_LIC_PORT", "9101"))
# How often we re-read the farm. Every served response is at most this stale,
# which is the window cuebot's in-flight correction has to cover.
SAMPLE_S = float(os.environ.get("SIM_LIC_SAMPLE_S", "4.0"))
PSQL = spec.psql_cmd()
ENV_KEY = os.environ.get("SIM_LIC_ENV_KEY", "CUE_LICENSES")

# Pool sizes. Deliberately small against a farm that could run far more, so the
# licenses -- not the cores -- are what binds.
HENGINE_SEATS = int(os.environ.get("SIM_LIC_HENGINE_SEATS", "8"))
KATANA_TOTAL = int(os.environ.get("SIM_LIC_KATANA_TOTAL", "120"))
MAYA_TOTAL = int(os.environ.get("SIM_LIC_MAYA_TOTAL", "60"))

# Artist workstations holding hengine seats before the farm starts, named so
# they can never collide with a sim render host (farm hosts are jaime/vrack/...).
ART_HOSTS = [h for h in os.environ.get(
    "SIM_LIC_ART_HOSTS", "artbox01,artbox02").split(",") if h]
# Katana seats artists try to take, and when they start trying. They can only
# get what is genuinely free, so this succeeding IS the headroom proof.
ART_KATANA = int(os.environ.get("SIM_LIC_ART_KATANA", "5"))
ART_KATANA_AT = float(os.environ.get("SIM_LIC_ART_KATANA_AT", "60"))
# SIM_LIC_NO_HOSTS=1 serves the contract WITHOUT the optional per-license `hosts`
# list, which is how a provider that only exposes counts behaves. cuebot is then
# blind to the machines outside the cue holding seats, so it must bound itself by
# `available` instead of by the license total, or it will open every seat the
# license has while artists already hold some.
NO_HOSTS = os.environ.get("SIM_LIC_NO_HOSTS", "0") == "1"

_lock = threading.Lock()
_state = {
    "queried_at": 0,
    "farm_frames": {},   # license -> RUNNING frames the farm holds
    "farm_hosts": {},    # license -> distinct farm hosts running it
    "art_katana_held": 0,
    "art_katana_wanted": 0,
    "samples": 0,
}


def _rows(sql):
    try:
        out = subprocess.run(PSQL + ["-t", "-A", "-F", "\t", "-c", sql],
                             capture_output=True, text=True, timeout=15).stdout
        return [ln.split("\t") for ln in out.strip().splitlines() if ln.strip()]
    except Exception:
        return []


def sample_farm():
    """What the farm is holding right now, per license name.

    One pass over running licensed frames. str_value is the layer's raw
    CUE_LICENSES value, so a layer declaring "katana,maya" is counted in BOTH
    pools -- it really did check out one of each.
    """
    frames, hosts = {}, {}
    for row in _rows(
            f"SELECT le.str_value, f.str_host FROM layer_env le "
            f"JOIN frame f ON f.pk_layer = le.pk_layer "
            f"WHERE le.str_key = '{ENV_KEY}' AND f.str_state = 'RUNNING';"):
        if len(row) < 2:
            continue
        raw, host = row[0], (row[1] or "").strip().lower()
        for name in [p.strip().lower() for p in raw.split(",") if p.strip()]:
            frames[name] = frames.get(name, 0) + 1
            if host:
                hosts.setdefault(name, set()).add(host)
    return frames, hosts


def sampler(t0):
    """Re-read the farm on a fixed cadence and let artists take what is free."""
    while True:
        # Stamp the sample with when the read STARTED, not when it returned. The
        # query sees a snapshot as of its start, and under load it can take a
        # second or more, so stamping it at the end would advertise the sample as
        # fresher than it is -- and cuebot, trusting that, would miss the frames
        # started during the read in its in-flight correction and over-book by
        # roughly one tick's worth. A real license server's timestamp means the
        # same thing: as of when the numbers were true.
        as_of = int(time.time())
        frames, hosts = sample_farm()
        elapsed = time.time() - t0
        with _lock:
            _state["farm_frames"] = frames
            _state["farm_hosts"] = {k: sorted(v) for k, v in hosts.items()}
            _state["queried_at"] = as_of
            _state["samples"] += 1
            # Artists start asking for katana partway through the run. They are
            # ordinary consumers: they get only what is actually free, and they
            # keep what they got. If cuebot's headroom works they get all of it
            # even with the farm flat out; if it does not, they get nothing --
            # which is precisely the complaint this feature exists to fix.
            if elapsed >= ART_KATANA_AT:
                _state["art_katana_wanted"] = ART_KATANA
                free = KATANA_TOTAL - frames.get("katana", 0) - _state["art_katana_held"]
                take = max(0, min(ART_KATANA - _state["art_katana_held"], free))
                _state["art_katana_held"] += take
        time.sleep(SAMPLE_S)


def licenses_payload():
    with _lock:
        frames = dict(_state["farm_frames"])
        hosts = {k: list(v) for k, v in _state["farm_hosts"].items()}
        queried_at = _state["queried_at"]
        art_katana = _state["art_katana_held"]

    # hengine: host-based. Seats are machines: the artists' workstations plus
    # every farm host currently running hengine work.
    hengine_hosts = sorted(set(ART_HOSTS) | set(hosts.get("hengine", [])))
    out = [
        {
            "name": "hengine",
            "feature": "Houdini Engine",
            "total": HENGINE_SEATS,
            # For a host-based pool `available` is seats, not frames.
            "available": max(0, HENGINE_SEATS - len(hengine_hosts)),
            "host_based": True,
            "hosts": [] if NO_HOSTS else [{"host": h, "count": 1} for h in hengine_hosts],
        },
        {
            "name": "katana",
            "feature": "Katana",
            "total": KATANA_TOTAL,
            "available": max(0, KATANA_TOTAL - frames.get("katana", 0) - art_katana),
            "host_based": False,
            "hosts": [] if NO_HOSTS else [{"host": h, "count": 1}
                                          for h in sorted(hosts.get("katana", []))],
        },
        {
            "name": "maya",
            "feature": "Maya",
            "total": MAYA_TOTAL,
            "available": max(0, MAYA_TOTAL - frames.get("maya", 0)),
            "host_based": False,
            "hosts": [] if NO_HOSTS else [{"host": h, "count": 1}
                                          for h in sorted(hosts.get("maya", []))],
        },
    ]
    return {"queried_at": queried_at, "licenses": out}


def state_payload():
    """Ground truth for the watcher: pool sizes, who holds what, farm usage."""
    with _lock:
        frames = dict(_state["farm_frames"])
        hosts = {k: list(v) for k, v in _state["farm_hosts"].items()}
        return {
            "queried_at": _state["queried_at"],
            "samples": _state["samples"],
            "totals": {"hengine": HENGINE_SEATS, "katana": KATANA_TOTAL,
                       "maya": MAYA_TOTAL},
            "host_based": {"hengine": True, "katana": False, "maya": False},
            "artist_holds": {"hengine": len(ART_HOSTS),
                             "katana": _state["art_katana_held"], "maya": 0},
            "artist_wanted": {"hengine": len(ART_HOSTS),
                              "katana": _state["art_katana_wanted"], "maya": 0},
            "artist_hosts": {"hengine": list(ART_HOSTS)},
            "farm_frames": frames,
            "farm_hosts": hosts,
        }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        if self.path.startswith("/licenses"):
            body = json.dumps(licenses_payload()).encode()
        elif self.path.startswith("/state"):
            body = json.dumps(state_payload()).encode()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *a):
        pass  # cuebot polls every few seconds; do not spam the log


def main():
    t0 = time.time()
    th = threading.Thread(target=sampler, args=(t0,), daemon=True)
    th.start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"fake license server on 127.0.0.1:{PORT}  "
          f"hengine={HENGINE_SEATS} seats (artists hold {len(ART_HOSTS)}), "
          f"katana={KATANA_TOTAL} (artists take {ART_KATANA} at t={ART_KATANA_AT:.0f}s), "
          f"maya={MAYA_TOTAL}; re-reads the farm every {SAMPLE_S:.0f}s", flush=True)
    # Progress lines mirror what cuebot is being told, so a failed run can be
    # read from this log alone.
    while time.time() - t0 < DURATION + 30:
        p = licenses_payload()
        parts = []
        for lic in p["licenses"]:
            kind = "seats" if lic["host_based"] else "frames"
            parts.append(f"{lic['name']} {lic['available']}/{lic['total']} free ({kind})")
        with _lock:
            art = _state["art_katana_held"]
        print(f"t={time.time()-t0:5.0f} | " + " | ".join(parts)
              + f" | artist katana held={art}", flush=True)
        time.sleep(5.0)
    srv.shutdown()


if __name__ == "__main__":
    main()
