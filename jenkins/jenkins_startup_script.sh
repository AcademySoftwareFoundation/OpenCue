#!/bin/sh

# TODO: configure SSL
# TODO: pull project ID from metadata

mkdir /root/jenkins_home
mount /dev/disk/by-id/google-jenkins-home /root/jenkins_home
chmod -R 777 /root/jenkins_home
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl start docker
gcloud auth configure-docker --quiet
docker pull gcr.io/opencue-test/opencue-jenkins
docker run -td -p 8080:8080 -v /root/jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock gcr.io/opencue-test/opencue-jenkins

