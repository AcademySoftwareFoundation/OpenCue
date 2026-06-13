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
Render a short demo image sequence and wire it up so the CueWeb frame preview
thumbnail viewer shows real rendered frames. A focused convenience wrapper
around the `blender` subcommand of load_test_jobs.py; Blender is used as the
renderer.

The sandbox RQD runs in a minimal Linux container (no Blender), so the host
Blender renders the frames straight into the shared RQD logs dir
(the cueweb container mounts it read-only) and a matching paused OpenCue job is
submitted with the layer's output path registered.

Cross-platform: Blender is auto-discovered on macOS, Windows and Linux
(CentOS / Rocky / Ubuntu / ...). Override with --blender, the $BLENDER env var,
or by putting `blender` on PATH.

Usage:
    python sandbox/render_blender_demo.py
    python sandbox/render_blender_demo.py --frames 6 --blender /path/to/blender
"""

import argparse
import os
import sys
import time

# Make the sibling load_test_jobs module importable no matter the cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import outline
import outline.cuerun
from outline.modules.shell import Shell

import opencue

from load_test_jobs import (
    DEFAULT_BLENDER_FRAMES,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SHOT,
    DEFAULT_SHOW,
    _blender_render,
    _find_job,
    discover_blender,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--blender", default=None,
                        help="path to the Blender executable (default: auto-detect "
                             "via $BLENDER, PATH, then common install locations)")
    parser.add_argument("--frames", type=int, default=DEFAULT_BLENDER_FRAMES,
                        help="frames to render (default: %(default)s)")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT,
                        help="shared dir for rendered frames; must be readable by "
                             "the cueweb container (default: %(default)s)")
    parser.add_argument("--show", default=DEFAULT_SHOW)
    parser.add_argument("--shot", default=DEFAULT_SHOT)
    args = parser.parse_args()

    blender_bin = args.blender or discover_blender()
    if not blender_bin or not os.path.exists(blender_bin):
        print("ERROR: Blender not found. Install it, add it to PATH, set $BLENDER, "
              "or pass --blender PATH.")
        print("  macOS:   /Applications/Blender.app/Contents/MacOS/Blender")
        print("  Windows: C:\\Program Files\\Blender Foundation\\Blender X.Y\\blender.exe")
        print("  Linux:   /usr/bin/blender (or snap/flatpak)")
        return 1
    print("Using Blender: %s" % blender_bin)

    stamp = "%d" % time.time_ns()
    render_dir = os.path.join(args.output_root, "blender_demo_%s" % stamp)
    os.makedirs(render_dir, exist_ok=True)
    output_spec = _blender_render(blender_bin, render_dir, args.frames)

    short_name = "blender_demo_%s" % stamp
    print("Submitting OpenCue job %s ..." % short_name)
    ol = outline.Outline(short_name, shot=args.shot, show=args.show)
    ol.add_layer(Shell(
        "beauty",
        command=["/bin/echo", "rendered", "frame", "#IFRAME#"],
        range="1-%d" % args.frames,
    ))
    # Paused so the instant marker frames don't finish and drop the job out of
    # Monitor Jobs before you can open it; the images exist regardless.
    outline.cuerun.launch(ol, pause=True, use_pycuerun=False)

    job = _find_job(short_name)
    layer = next(l for l in job.getLayers() if l.name() == "beauty")
    layer.registerOutputPath(output_spec)

    print("-" * 60)
    print("Job:    %s" % job.name())
    print("Layer:  beauty   output: %s" % output_spec)
    print("Open the job in CueWeb -> Frames -> click the Preview (image) icon")
    print("on a frame to see the Blender render.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
