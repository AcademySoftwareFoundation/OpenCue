#!/bin/bash

# Checks that a release bundle holds every file a release publishes, with the Python packages
# versioned as the build. Their version is the build ID in PEP 440 form, where a branch build
# 1.2.3-abc123 becomes 1.2.3+abc123.
#
#   ci/check_release_bundle.sh <BUILD_ID> <BUNDLE_DIRECTORY>

set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <BUILD_ID> <BUNDLE_DIRECTORY>"
  exit 1
fi

build_id="$1"
python_version="${build_id/-/+}"
cd "$2"

expected=(
  LICENSE
  VERSION
  build_metadata.json
  "schema-${build_id}.sql"
  "seed_data-${build_id}.sql"
  "cuebot-${build_id}-all.jar"
  "opencue-cuebot-${build_id}-1.noarch.rpm"
)
for target in x86_64-unknown-linux-gnu x86_64-unknown-linux-musl x86_64-apple-darwin \
    aarch64-apple-darwin; do
  expected+=("openrqd-${build_id}-${target}")
done
expected+=("openrqd-${build_id}-x86_64-pc-windows-msvc.exe")

missing=0
for file in "${expected[@]}"; do
  if [[ ! -s "${file}" ]]; then
    echo "Missing: ${file}"
    missing=1
  fi
done

for package in proto pycue pyoutline cueadmin cueman cuecmd cuesubmit cuegui rqd cuenimby; do
  for file in "opencue_${package}-${python_version}-py3-none-any.whl" \
      "opencue_${package}-${python_version}.tar.gz"; do
    if [[ ! -s "${file}" ]]; then
      echo "Missing: ${file}"
      missing=1
    fi
  done
done

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi
echo "The bundle holds every release file for ${build_id}."
