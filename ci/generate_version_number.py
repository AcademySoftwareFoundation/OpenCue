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
Generates the OpenCue version number of the current commit.

Version number is derived using two sources:

  1. `VERSION.in`. This file contains the current major and minor version of
     OpenCue, for example `0.3`. It should be updated manually by developers
     when needed.
  2. Git repository history.

Script output will contain the major, minor, and patch version of the codebase,
for example `0.3.27`. The patch version is generated automatically from the
repository Git history.

Commits in the master branch get a patch version by number of commits since
VERSION.in was last updated. Commits in any other branch get a patch version
containing the Git commit hash, based on the next potential patch number.

Some OpenCue tools expect this version information to be contained in a `VERSION`
file in the top level of the repository. To generate this file, change to the
root directory of your Git clone and run this script:

  $ ci/generate_version_number.py > ./VERSION

This step is already performed automatically within our CI pipelines.
"""

import pathlib
import re
import subprocess
import sys
from typing import List

def run_command(cmd: List[str]) -> str:
    """Runs a command and returns its stripped stdout."""
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(
            f"Command '{' '.join(cmd)}' failed with error:\n{e.stderr}",
            file=sys.stderr,
        )
        raise


def get_current_branch() -> str:
    """Determines the current git branch, handling detached HEAD states."""
    try:
        # Modern way, works unless in detached HEAD.
        branch = run_command(["git", "branch", "--show-current"])
        if branch:
            return branch
    except subprocess.CalledProcessError:
        # Fallback for older git versions or other issues.
        pass

    # Fallback for detached HEAD state (common in CI).
    # This replicates:
    # git branch --remote --verbose --no-abbrev --contains | sed -rne 's/^[^\/]*\/([^\ ]+).*$/\1/p'
    output = run_command(["git", "branch", "--remote", "--verbose", "--no-abbrev", "--contains"])
    for line in output.splitlines():
        line = line.strip()
        if "->" in line:  # Skip lines like 'origin/HEAD -> origin/master'
            continue
        # Regex to find 'origin/branch-name' and extract 'branch-name'
        match = re.match(r"^[^\/]+\/([^ ]+)", line)
        if match:
            return match.group(1)

    raise RuntimeError("Could not determine git branch.")


def get_full_version(versionType="") -> str:
    """
    Generates and returns the full version string based on Git history.

    Raises:
        FileNotFoundError: If VERSION.in is not found.
        RuntimeError: If the git branch cannot be determined.
        subprocess.CalledProcessError: If a git command fails.

    Returns:
        The calculated version string.
    """
    script_dir = pathlib.Path(__file__).parent.resolve()
    toplevel_dir = script_dir.parent
    version_in_path = toplevel_dir / "VERSION.in"

    if not version_in_path.is_file():
        raise FileNotFoundError(f"Version file not found at {version_in_path}")

    # Remove all whitespace to match the original shell script's `sed 's/[[:space:]]//g'`.
    version_file_content = version_in_path.read_text(encoding="utf-8")
    version_major_minor = "".join(version_file_content.split())
    current_branch = get_current_branch()

    last_version_commit = run_command(
        ["git", "log", "--follow", "-1", "--pretty=%H", str(version_in_path)]
    )

    if current_branch == "master":
        commit_count = run_command(["git", "rev-list", "--count", f"{last_version_commit}..HEAD"])
        print(f"Commit count since last release: {commit_count}", file=sys.stderr)
        full_version = f"{version_major_minor}.{commit_count}"
    else:
        print(f"version file last changed commit: {last_version_commit}", file=sys.stderr)
        count_in_master = run_command(["git", "rev-list", "--count", f"{last_version_commit}..origin/master"])
        print(f"Commit count in master since last release: {count_in_master}", file=sys.stderr)
        short_hash = run_command(["git", "rev-parse", "--short", "HEAD"])
        # For feature branches, use the next patch number + commit hash
        full_version = f"{version_major_minor}.{int(count_in_master) + 1}+{short_hash}"
        if versionType == "docker":
            full_version = f"{version_major_minor}.{int(count_in_master) + 1}-{short_hash}"

    return full_version

def main():
    """Generates and prints the full version string."""
    try:
        version = get_full_version(versionType="docker")
        print(version)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as e:
        print(f"Error: Could not generate version number.\n{e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
else:
    __version__ = get_full_version()
