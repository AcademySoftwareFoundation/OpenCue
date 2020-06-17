#!/bin/bash

# Generates the OpenCue version number of the current commit.
#
# Version number is derived using two sources:
#
#   1. `VERSION.in`. This file contains the current major and minor version of OpenCue, for example
#      `0.3`. It should be updated manually by developers when needed.
#   2. Git repository history.
#
# Script output will contain the major, minor, and patch version of the codebase, for example
# `0.3.27`. Patch version is generated automatically from the repository Git history.
#
# Commits in the master branch get a patch version by number of commits since VERSION.in was
# last updated. Commits in any other branch get a patch version containing the Git commit hash.
#
# Some OpenCue tools expect this version information to be contained in a `VERSION` file in the
# top level of the repository. To generate this file, change to the root directory of your Git
# clone and run this script:
#
#   $ ci/generate_version_number.sh > ./VERSION
#
# This step is already performed automatically within our CI pipelines.
#
# NOTE: To run this script on macOS, you need to have `gsed` installed:
#
#   $ brew install gnu-sed
#

set -e

script_dir="$(cd "$(dirname "$0")" && pwd)"
toplevel_dir="$(dirname "$script_dir")"

version_in="$toplevel_dir/VERSION.in"

if [[ "$(uname -s)" = "Darwin" ]]; then
  sed_cmd="gsed"
else
  sed_cmd="sed"
fi

version_major_minor="$(cat "$version_in" | sed 's/[[:space:]]//g')"
current_branch="$(git branch --show-current)"
>&2 echo "Current branch: ${current_branch}"

git fetch origin

if [[ "$current_branch" = "master" ]]; then
  commit_count=$(git rev-list --count $(git log --follow -1 --pretty=%H "$version_in")..HEAD)
  full_version="${version_major_minor}.${commit_count}"
else
  commit_count_in_master=$(git rev-list --count $(git log --follow -1 --pretty=%H "$version_in")..origin/master)
  commit_short_hash=$(git rev-parse --short HEAD)
  full_version="${version_major_minor}.$((commit_count_in_master + 1))-${commit_short_hash}"
fi

echo ${full_version}
