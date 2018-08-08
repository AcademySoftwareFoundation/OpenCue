#!/bin/sh

set -e

GCP_PROJECT=queue-manager-dev

cd $(dirname $0)/..

docker build -t cue3-bot .
docker tag cue3-bot gcr.io/$GCP_PROJECT/cuebot:${USER}
