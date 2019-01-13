#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

if [[ -z "${CUE_PUBLISH_BUCKET}" ]]; then
  echo "CUE_PUBLISH_BUCKET must be defined"
  exit 1
fi

gsutil -m cp \
  "${artifact_directory}/cuebot-${build_id}-all.jar" \
  "${artifact_directory}/rqd-${build_id}-all.tar.gz" \
  "${artifact_directory}/pycue-${build_id}-all.tar.gz" \
  "${artifact_directory}/cuegui-${build_id}-all.tar.gz" \
  "gs://${CUE_PUBLISH_BUCKET}/${build_id}/"

# TODO(bcipriano) Publish Docker images to DockerHub.

