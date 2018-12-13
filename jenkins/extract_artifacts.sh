#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

build_id=$1
artifact_directory=$2

mkdir -p "$artifact_directory"
container_id=$(docker create opencue/cuebot:$build_id)
docker cp $container_id:/opt/cue3/cuebot.jar $artifact_directory/
docker rm $container_id

