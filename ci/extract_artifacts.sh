#!/bin/bash

set -e

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

if [[ -z "${BUILD_SOURCEVERSION}" ]]; then
  echo 'Environment var BUILD_SOURCEVERSION must be set.'
  exit 1
fi

mkdir -p "${artifact_directory}"

cp LICENSE VERSION "${artifact_directory}/"

echo "{\"git_commit\": \"${BUILD_SOURCEVERSION}\"}" | tee "${artifact_directory}/build_metadata.json"
