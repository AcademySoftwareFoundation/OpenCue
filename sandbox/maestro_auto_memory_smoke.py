#!/usr/bin/env python3

#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
Sandbox smoke test for Maestro auto memory (docs/_docs/developer-guide/maestro.md 3.9).

Submits one layer whose frames allocate --base-mb each, except --outlier-frame, which
allocates --outlier-mb and holds it. Then it checks, against a running sandbox with
Maestro on and the show scheduler-managed:

  1. While the outlier runs, a PST-style edit lowering the layer's Minimum Memory
     is not written back up by host reports.
  2. Once maestro.probe_frames frames succeeded, the layer books from their rss
     percentile (layer_mem.int_mem_booked), far below the outlier.
  3. The outlier frame, if RQD killed it for memory, retried (informational: it
     depends on the RQD memory limits of the sandbox).

Exits 0 when checks 1 and 2 pass. Example:

  python sandbox/maestro_auto_memory_smoke.py --show testing
"""

import argparse
import sys
import time

import opencue
import outline
import outline.cuerun
from outline.modules.shell import Shell


ALLOCATE = ("import sys, time; b = bytearray(int(sys.argv[1]) * 1024 * 1024); "
            "time.sleep(int(sys.argv[2]))")


def _command(args):
    script = ("if [ #IFRAME# -eq {outlier} ]; then MB={big}; HOLD={hold_big}; "
              "else MB={base}; HOLD={hold}; fi; python3 -c '{alloc}' $MB $HOLD").format(
                  outlier=args.outlier_frame, big=args.outlier_mb, base=args.base_mb,
                  hold=args.hold_seconds, hold_big=args.hold_seconds * 6, alloc=ALLOCATE)
    return ["/bin/bash", "-c", script]


def _layer(job_name):
    return opencue.api.findLayer(job_name, "auto_mem")


def _frame(layer, number):
    for frame in layer.getFrames():
        if frame.number() == number:
            return frame
    return None


def _status(layer):
    stats = layer.data.layer_stats
    return ("ask=%dM booked=%dM auto=%s succeeded=%d running=%d" % (
        layer.minMemory() // 1024, layer.bookedMemory() // 1024, layer.isAutoMemory(),
        stats.succeeded_frames, stats.running_frames))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", default="testing")
    parser.add_argument("--shot", default="smoke")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--base-mb", type=int, default=200)
    parser.add_argument("--outlier-frame", type=int, default=3)
    parser.add_argument("--outlier-mb", type=int, default=4000)
    parser.add_argument("--ask-mb", type=int, default=2048)
    parser.add_argument("--hold-seconds", type=int, default=20)
    parser.add_argument("--probe-frames", type=int, default=8,
                        help="maestro.probe_frames of the Cuebot under test")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds")
    args = parser.parse_args()

    if not opencue.api.findShow(args.show).schedulerManaged():
        print("WARNING: show %s is not flagged scheduler-managed; unless Maestro runs in "
              "facility mode, this tests the legacy dispatcher." % args.show)

    short_name = "auto_mem_smoke_%d" % int(time.time())
    ol = outline.Outline(short_name, shot=args.shot, show=args.show)
    ol.add_layer(Shell("auto_mem", command=_command(args), range="1-%d" % args.frames,
                       memory="%dm" % args.ask_mb))
    job = outline.cuerun.launch(ol, use_pycuerun=False)[0]
    job_name = job.name()
    print("Submitted %s" % job_name)

    deadline = time.time() + args.timeout
    lowered_kb = None
    pin_ok = None
    booked_ok = None
    while time.time() < deadline:
        layer = _layer(job_name)
        print(_status(layer))
        outlier = _frame(layer, args.outlier_frame)

        # Check 1: lower the ask while the outlier runs; it must stay lowered.
        if lowered_kb is None and outlier is not None and \
                outlier.state() == opencue.api.job_pb2.RUNNING:
            lowered_kb = layer.minMemory() // 2
            layer.setMinMemory(lowered_kb)
            lowered_at = time.time()
            print("Lowered Minimum Memory to %dM while the outlier runs" % (lowered_kb // 1024))
        elif lowered_kb is not None and pin_ok is None and time.time() - lowered_at > 90:
            pin_ok = layer.minMemory() == lowered_kb
            print("CHECK 1 %s: Minimum Memory %dM after three report cycles (set %dM)" % (
                "PASS" if pin_ok else "FAIL", layer.minMemory() // 1024, lowered_kb // 1024))

        # Check 2: after the probe, the booked size follows the bulk, not the outlier.
        stats = layer.data.layer_stats
        if booked_ok is None and stats.succeeded_frames > args.probe_frames and \
                layer.bookedMemory() > 0:
            booked_ok = layer.bookedMemory() < args.outlier_mb * 1024 // 2
            print("CHECK 2 %s: booked %dM with the outlier at %dM" % (
                "PASS" if booked_ok else "FAIL", layer.bookedMemory() // 1024,
                args.outlier_mb))

        if stats.pending_frames == 0 and stats.running_frames == 0:
            break
        time.sleep(15)

    outlier = _frame(_layer(job_name), args.outlier_frame)
    if outlier is None:
        print("CHECK 3 (info): outlier frame %d not found" % args.outlier_frame)
    else:
        print("CHECK 3 (info): outlier frame %s, %d retries" % (
            opencue.api.job_pb2.FrameState.Name(outlier.state()), outlier.retries()))

    if pin_ok is None or booked_ok is None:
        print("FAIL: timed out before every check ran (pin=%s booked=%s)" % (pin_ok, booked_ok))
        return 1
    return 0 if pin_ok and booked_ok else 1


if __name__ == "__main__":
    sys.exit(main())
