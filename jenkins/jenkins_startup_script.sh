#!/bin/sh

set -e

# Wait for networking to be fully up.
# TODO(cipriano) Improve this check.
sleep 30

mount_point="/root/jenkins_home"
mkdir -p ${mount_point}
mount /dev/disk/by-id/google-jenkins-home ${mount_point}
chmod -R 777 ${mount_point}

yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl start docker

project_id=$(curl "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")
image_tag=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/opencue-image-tag" -H "Metadata-Flavor: Google")
gcloud auth configure-docker --quiet
docker pull gcr.io/${project_id}/opencue-jenkins:${image_tag}
docker run -td \
  -p 8080:8080 \
  -v ${mount_point}:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gcr.io/${project_id}/opencue-jenkins:${image_tag}

# TODO(cipriano) Configure SSL - generate cert and configure ports via Jenkins CLI options.

