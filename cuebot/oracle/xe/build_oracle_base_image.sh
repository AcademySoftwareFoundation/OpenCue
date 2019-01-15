#!/bin/sh

set -e

timestamp=$(date +%Y%m%d%H%M%S)


INSTANCE_NAME="oracle-build-$timestamp"
ZONE="us-central1-c"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
IMAGE_NAME="oracle-base-$timestamp"

echo "Starting instance $INSTANCE_NAME..."

gcloud --project $PROJECT_ID compute instances create $INSTANCE_NAME \
  --machine-type=n1-standard-2 --network=default --zone=$ZONE \
  --image-project=eip-images --image-family=centos-7-drawfork

INSTANCE_IP=$(gcloud --project $PROJECT_ID compute instances describe $INSTANCE_NAME \
  --zone $ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "Waiting for instance to become available..."

sleep 60

ssh $SSH_OPTS $INSTANCE_IP sudo yum install -y yum-utils device-mapper-persistent-data lvm2
ssh $SSH_OPTS $INSTANCE_IP sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
ssh $SSH_OPTS $INSTANCE_IP sudo yum install -y docker-ce

script_path=$(dirname $0)/setupDB.sh
script_dest="/etc/opencue/"
ssh $SSH_OPTS $INSTANCE_IP sudo mkdir $script_dest
ssh $SSH_OPTS $INSTANCE_IP sudo chmod 777 $script_dest
scp $script_path $INSTANCE_IP:$script_dest

gcloud --project $PROJECT_ID --quiet compute instances delete $INSTANCE_NAME \
  --zone=$ZONE --keep-disks=boot
gcloud --project $PROJECT_ID compute images create $IMAGE_NAME \
  --family=cue-oracle-base --source-disk=$INSTANCE_NAME --source-disk-zone=$ZONE

echo "Image $IMAGE_NAME created."

