#!/bin/bash

# Helper script for creating a Jenkins instance. This script is used by the
# OpenCue Project Authors to maintain the official Jenkins setup and is
# included here as a convenience in the event you want to create your own
# Jenkins setup for builds and testing. A typical OpenCue deployment will not
# need to run a Jenkins instance.

# This script makes the following assumptions:
#   - The GCP project named by CUE_GCP_PROJECT_ID must exist.
#   - The network named by NETWORK must exist.
#   - The static IP named by JENKINS_STATIC_IP must exist and not be in use.
#   - The disk named by DISK_NAME must exist in ZONE, formatted and ready to use.
#     The intent is for you to reuse the disk from your old jenkins instance, to
#     preserve existing config in the event you need to replace the instance.

set -e

if [ -z "$CUE_GCP_PROJECT_ID" ]; then
  echo "You must set the CUE_GCP_PROJECT_ID env var"
  exit 1
fi

if [ -z "$CUE_PUBLISH_BUCKET" ]; then
  echo "You must set the CUE_PUBLISH_BUCKET env var"
  exit 1
fi

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
INSTANCE_NAME="opencue-jenkins-${TIMESTAMP}"
INSTANCE_TYPE="n1-standard-4"
DISK_NAME="opencue-jenkins-home"
IP_NAME="opencue-jenkins"
ZONE="us-central1-c"
NETWORK="jenkins"
IMAGE_NAME="gcr.io/${CUE_GCP_PROJECT_ID}/opencue-jenkins:${TIMESTAMP}"

docker build -t ${IMAGE_NAME} .
gcloud auth configure-docker --quiet
docker push ${IMAGE_NAME}

external_ip=$(gcloud compute addresses list \
  --project ${CUE_GCP_PROJECT_ID} \
  --filter="name=('opencue-jenkins')" \
  --format="value(address)")

gcloud compute instances create ${INSTANCE_NAME} \
    --project=${CUE_GCP_PROJECT_ID} \
    --zone=${ZONE} \
    --network=${NETWORK} \
    --machine-type=${INSTANCE_TYPE} \
    --image-project=centos-cloud \
    --image-family=centos-7 \
    --boot-disk-size=100G \
    --disk=name=${DISK_NAME},device-name=jenkins-home \
    --address=${external_ip} \
    --scopes=https://www.googleapis.com/auth/devstorage.read_write \
    --metadata=opencue-image-tag=${TIMESTAMP},opencue-publish-bucket=${CUE_PUBLISH_BUCKET} \
    --metadata-from-file=startup-script=./jenkins_startup_script.sh

