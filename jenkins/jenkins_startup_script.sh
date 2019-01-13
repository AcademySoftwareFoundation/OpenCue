#!/bin/sh

set -e

# Wait for networking to be fully up.
# TODO(cipriano) Improve this check.
sleep 30

MOUNT_POINT="/root/jenkins_home"
PROJECT_ID=$(curl "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")
IMAGE_TAG=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/opencue-image-tag" -H "Metadata-Flavor: Google")
PUBLISH_BUCKET=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/opencue-publish-bucket" -H "Metadata-Flavor: Google")

mkdir -p ${MOUNT_POINT}
mount /dev/disk/by-id/google-jenkins-home ${MOUNT_POINT}
chmod -R 777 ${MOUNT_POINT}

yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl start docker

# This relies on the listed SSL keystore to have been configured. If you
# haven't done this, you can disable the following two lines and use standard
# HTTP instead.
server_port="443:8443"
jenkins_opts="--httpPort=-1 --httpsPort=8443 --httpsKeyStore=/var/jenkins_home/jenkins.jks --httpsKeyStorePassword=$(cat ${MOUNT_POINT}/jenkins.jks_pass)"

# Uncomment this if you want to use standard HTTP instead.
# server_port="8080:8080"

gcloud auth configure-docker --quiet
docker pull gcr.io/${PROJECT_ID}/opencue-jenkins:${IMAGE_TAG}
docker run -td \
  --publish $server_port \
  --env JENKINS_OPTS="$jenkins_opts" \
  --env CUE_PUBLISH_BUCKET="${PUBLISH_BUCKET}" \
  --volume ${MOUNT_POINT}:/var/jenkins_home \
  --volume /var/run/docker.sock:/var/run/docker.sock \
  gcr.io/${PROJECT_ID}/opencue-jenkins:${IMAGE_TAG}

