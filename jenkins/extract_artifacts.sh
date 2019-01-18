#!/bin/sh

set -e

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

if [[ -z "${GIT_COMMIT}" ]]; then
  print 'Environment var GIT_COMMIT must be set.'
  exit 1
fi

mkdir -p "$artifact_directory"

echo "{\"git_commit\": \"${GIT_COMMIT}\"}" | tee "${artifact_directory}/build_metadata.json"

container_id=$(docker create opencue/cuebot:${build_id})
docker cp $container_id:/opt/opencue/cuebot-${build_id}-all.jar "$artifact_directory/"
docker rm $container_id

for component in rqd pycue pyoutline cuegui cuesubmit; do
  container_id=$(docker create opencue/${component}:${build_id})
  docker cp $container_id:/opt/opencue/${component}-${build_id}-all.tar.gz "$artifact_directory/"
  docker rm $container_id
done

