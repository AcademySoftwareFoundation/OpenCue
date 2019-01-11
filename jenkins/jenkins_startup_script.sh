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

# This relies on the listed SSL keystore to have been configured. If you
# haven't done this, you can disable the following two lines and use standard
# HTTP instead.
server_port="443:8443"
jenkins_opts="--httpPort=-1 --httpsPort=8443 --httpsKeyStore=/var/jenkins_home/jenkins.jks --httpsKeyStorePassword=$(cat ${mount_point}/jenkins.jks_pass)"

# Uncomment this if you want to use standard HTTP instead.
# server_port="8080:8080"

project_id=$(curl "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")
image_tag=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/opencue-image-tag" -H "Metadata-Flavor: Google")
gcloud auth configure-docker --quiet
docker pull gcr.io/${project_id}/opencue-jenkins:${image_tag}
docker run -td \
  -p $server_port \
  --env JENKINS_OPTS="$jenkins_opts" \
  -v ${mount_point}:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gcr.io/${project_id}/opencue-jenkins:${image_tag}

