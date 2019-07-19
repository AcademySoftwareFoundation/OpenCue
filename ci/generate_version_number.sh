#!/bin/bash

set -e

script_dir="$(cd "$(dirname "$0")" && pwd)"
toplevel_dir="$(dirname "$script_dir")"

version_in="$toplevel_dir/VERSION.in"

version_major_minor="$(cat "$version_in" | sed 's/[[:space:]]//g')"
current_branch="$(git branch --remote --verbose --no-abbrev --contains | sed -rne 's/^[^\/]*\/([^\ ]+).*$/\1/p')"

if [[ "$current_branch" = "master" ]]; then
  commit_count=$(git rev-list --count $(git log --follow -1 --pretty=%H "$version_in")..HEAD)
  full_version="${version_major_minor}.${commit_count}"
else
  commit_count_in_master=$(git rev-list --count $(git log --follow -1 --pretty=%H "$version_in")..origin/master)
  commit_short_hash=$(git rev-parse --short HEAD)
  full_version="${version_major_minor}.$((commit_count_in_master + 1))-${commit_short_hash}"
fi

echo ${full_version}
