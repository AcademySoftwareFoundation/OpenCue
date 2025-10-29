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

"""Helper script to execute commands from a file based on frame number and chunk size."""

import argparse
import subprocess
import sys


def main():
    """Execute commands from a file based on frame number and chunk size."""
    parser = argparse.ArgumentParser(
        description="Execute commands from a file based on frame number and chunk size."
    )
    parser.add_argument("command_file", help="Path to the file containing commands")
    parser.add_argument(
        "chunk_size", type=int, help="Number of commands to execute per frame"
    )
    parser.add_argument(
        "--frame", type=int, required=True, help="Frame number to execute"
    )

    args = parser.parse_args()

    # Read all commands from the file
    with open(args.command_file, "r", encoding="utf-8") as f:
        commands = [line.strip() for line in f if line.strip()]

    # Calculate which commands to run for this frame
    start_idx = (args.frame - 1) * args.chunk_size
    end_idx = min(start_idx + args.chunk_size, len(commands))

    if start_idx >= len(commands):
        print(f"Frame {args.frame} is beyond the available commands")
        return 0

    # Execute each command in the chunk
    for idx in range(start_idx, end_idx):
        cmd = commands[idx]
        print(f"Executing command {idx + 1}: {cmd}")

        # Execute the command
        result = subprocess.run(cmd, shell=True, check=False)

        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}: {cmd}")
            sys.exit(result.returncode)

    return 0


if __name__ == "__main__":
    main()
