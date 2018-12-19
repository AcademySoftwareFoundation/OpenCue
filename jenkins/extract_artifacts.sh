#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

mkdir -p "$artifact_directory"

container_id=$(docker create opencue/cuebot:$build_id)
docker cp $container_id:/opt/cue3/cuebot.jar "$artifact_directory/"
docker rm $container_id

container_id=$(docker create opencue/rqd:$build_id)
docker cp $container_id:/opt/cue3/rqd-0.1-all.tar.gz "$artifact_directory/"
docker rm $container_id

container_id=$(docker create opencue/pycue:$build_id)
docker cp $container_id:/opt/cue3/pycue-0.1-all.tar.gz "$artifact_directory/"
docker rm $container_id

container_id=$(docker create opencue/cuegui:$build_id)
docker cp $container_id:/opt/cue3/cuegui-0.1-all.tar.gz "$artifact_directory/"
docker rm $container_id

