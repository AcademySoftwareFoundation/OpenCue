#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

# TODO re-enable these changes, once the vars are used
# if [[ -z "${CUE_PUBLISH_BUCKET}" ]]; then
#   echo "CUE_PUBLISH_BUCKET must be defined"
#   exit 1
# fi

# if [[ -z "${CUE_PUBLISH_PROJECT}" ]]; then
#   echo "CUE_PUBLISH_PROJECT must be defined"
#   exit 1
# fi

# TODO publish JAR to GCS
# TODO publish RQD tarball to GCS
# TODO publish images to GCR

