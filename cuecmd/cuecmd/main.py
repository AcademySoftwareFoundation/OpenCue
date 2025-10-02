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
Cuecmd - Execute a list of commands on the OpenCue render farm.

This tool reads a file containing a list of commands and submits them as
frames to be executed on the render farm. Commands can be chunked together
to run multiple commands per frame.
"""

import argparse
import math
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import outline
from outline.modules.shell import Shell


def parse_arguments(argv):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute a list of commands on the OpenCue render farm.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s commands.txt
  %(prog)s commands.txt --chunk 5 --cores 2 --memory 4
  %(prog)s commands.txt --pause --pretend
        """,
    )

    parser.add_argument(
        "command_file", help="A file with a list of commands to run (one per line)"
    )

    parser.add_argument(
        "-c",
        "--chunk",
        type=int,
        default=1,
        help="Number of commands to chunk per frame (Default: 1)",
    )

    parser.add_argument(
        "--cores",
        type=float,
        default=1.0,
        help="Number of cores required per frame (Default: 1.0)",
    )

    parser.add_argument(
        "--memory",
        type=float,
        default=1.0,
        help="Amount of RAM in GB required per frame (Default: 1.0)",
    )

    parser.add_argument(
        "-p", "--pause", action="store_true", help="Launch the job in the paused state"
    )

    parser.add_argument(
        "--pretend",
        action="store_true",
        help="Generate the outline and print the launch info without submitting",
    )

    parser.add_argument(
        "-s",
        "--shot",
        default=os.environ.get("SHOT", "default"),
        help='Shot name for the job (Default: from $SHOT or "default")',
    )

    parser.add_argument(
        "--show",
        default=os.environ.get("SHOW", "default"),
        help='Show name for the job (Default: from $SHOW or "default")',
    )

    parser.add_argument(
        "--user",
        default=os.environ.get("USER", "unknown"),
        help='User name for the job (Default: from $USER or "unknown")',
    )

    parser.add_argument(
        "--job-name", help="Custom job name (Default: auto-generated from file name)"
    )

    return parser.parse_args(argv[1:])


def count_commands(command_file):
    """Count the number of non-empty commands in the file."""
    count = 0
    with open(command_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def get_frame_range(command_count, chunk_size):
    """Calculate the frame range based on command count and chunk size."""
    num_frames = math.ceil(command_count / chunk_size)
    return f"1-{num_frames}"


def copy_to_temp(command_file):
    """Copy the command file to a temporary location that will be accessible during execution."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="cuecmd_")
    basename = Path(command_file).stem
    temp_file = os.path.join(temp_dir, f"{basename}.cmds")
    shutil.copyfile(command_file, temp_file)
    return temp_file


def create_outline(args, command_file, frame_range):
    """Create an outline for executing the commands."""
    # Get the path to the execute_commands.py script
    execute_script = os.path.join(os.path.dirname(__file__), "execute_commands.py")

    # Create the job name
    if args.job_name:
        job_name = args.job_name
    else:
        basename = Path(args.command_file).stem
        job_name = f"{args.show}_{args.shot}_{args.user}_{basename}"

    # Create the outline
    ol = outline.Outline(job_name, shot=args.shot, show=args.show, user=args.user)

    # Create the shell command that will execute the commands
    # Use python3 explicitly
    cmd = f"python3 {execute_script} {command_file} {args.chunk} --frame #IFRAME#"

    # Create the layer
    layer = Shell(
        "cuecmd",
        command=cmd,
        chunk=1,
        threads=args.cores,
        threadable=1,
        range=frame_range,
        memory=f"{int(args.memory * 1024)}MB",
    )

    ol.add_layer(layer)
    return ol


def main(argv=None):
    """Main entry point for cuecmd."""
    if argv is None:
        argv = sys.argv

    args = parse_arguments(argv)

    # Validate the command file exists
    if not os.path.isfile(args.command_file):
        print(f"Error: Command file not found: {args.command_file}", file=sys.stderr)
        sys.exit(1)

    # Get absolute path to the command file
    command_file = os.path.abspath(args.command_file)

    # Count commands and calculate range
    command_count = count_commands(command_file)
    if command_count == 0:
        print("Error: No commands found in the command file", file=sys.stderr)
        sys.exit(1)

    print(f"Found {command_count} commands in {command_file}")

    frame_range = get_frame_range(command_count, args.chunk)
    print(f"Frame range with chunking of {args.chunk}: {frame_range}")

    # Copy command file to a temporary location
    temp_command_file = copy_to_temp(command_file)
    print(f"Copied commands to: {temp_command_file}")

    # Create the outline
    ol = create_outline(args, temp_command_file, frame_range)

    if args.pretend:
        print("\n=== Pretend Mode ===")
        print(f"Job name: {ol.get_name()}")
        print(f"Shot: {ol.get_shot()}")
        print(f"Show: {ol.get_show()}")
        print(f"User: {ol.get_user()}")
        print(f"Frame range: {frame_range}")
        print(f"Chunk size: {args.chunk}")
        print(f"Cores per frame: {args.cores}")
        print(f"Memory per frame: {args.memory}GB")
        print(f"Command file: {temp_command_file}")
        print("\nWould launch the job with the above settings.")
        return 0

    # Launch the job
    try:
        jobs = outline.cuerun.launch(ol, pause=args.pause, use_pycuerun=True)
        if jobs:
            print(f"\nSuccessfully launched job: {ol.get_name()}")
            if args.pause:
                print("Job is paused. Use cueadmin to unpause it.")
        else:
            print("Failed to launch job", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error launching job: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
