#!/bin/bash

# Helper script for creating a Jenkins instance. This script is used by the
# OpenCue Project Authors to maintain the official Jenkins setup and is
# included here as a convenience in the event you want to create your own
# Jenkins setup for builds and testing. A typical OpenCue deployment will not
# need to run a Jenkins instance.

# This script makes the following assumptions:
#   - The GCP project named by GCP_TEST_PROJECT must exist.
#   - The network named by NETWORK must exist.
#   - The static IP named by JENKINS_STATIC_IP must exist and not be in use.
#   - The disk named by DISK_NAME must exist in ZONE, formatted and ready to use.
#     The intent is for you to reuse the disk from your old jenkins instance, to
#     preserve existing config in the event you need to replace the instance.

set -e

if [ -z "$GCP_TEST_PROJECT" ]; then
  echo "You must set the GCP_TEST_PROJECT env var"
  exit 1
fi
# opencue-test

if [ -z "$JENKINS_STATIC_IP" ]; then
  echo "You must set the JENKINS_STATIC_IP env var"
  exit 1
fi
# 35.193.200.128

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
INSTANCE_NAME="opencue-jenkins-${TIMESTAMP}"
INSTANCE_TYPE="n1-standard-8"
DISK_NAME="opencue-jenkins-home"
ZONE="us-central1-c"
NETWORK="jenkins"
IMAGE_NAME="gcr.io/${GCP_TEST_PROJECT}/opencue-jenkins:${TIMESTAMP}"

docker build -t ${IMAGE_NAME} .
gcloud auth configure-docker --quiet
docker push ${IMAGE_NAME}

gcloud compute instances create ${INSTANCE_NAME} \
    --project=${GCP_TEST_PROJECT} \
    --zone=${ZONE} \
    --network=${NETWORK} \
    --machine-type=${INSTANCE_TYPE} \
    --image-project=centos-cloud \
    --image-family=centos-7 \
    --disk=name=${DISK_NAME},device-name=jenkins-home \
    --address=${JENKINS_STATIC_IP} \
    --metadata=opencue-image-tag=${TIMESTAMP} \
    --metadata-from-file=startup-script=./jenkins_startup_script.sh

