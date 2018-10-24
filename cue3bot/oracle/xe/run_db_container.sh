#!/bin/sh

set -e

cd $(dirname $0)

DEP_BUCKET="GCS BUCKET NAME" # Where the oracle rpm was copied.

XE_DIRECTORY=`pwd`
CUEBOT_ROOT_DIRECTORY=$(dirname $(dirname $XE_DIRECTORY))
ORACLE_RPM="oracle-xe-11.2.0-1.0.x86_64.rpm.zip"
ORACLE_DOCKER_REPO="https://github.com/oracle/docker-images.git"
DOCKER_NAME="oracle-xe"
ORACLE_SQL_FILE='/tmp/oracle_ddl/db-schema.sql'
CUE_DB_USER='CUE3'


if (( $# < 2 )); then
  echo "Please pass a password as the first argument!"
  echo "Usage:"
  echo "   ./run_db_container.sh sys_db_password cue3_db_password [--build-prod]"
  exit 1
fi

if [ ! -d "./docker_setup" ]; then
  mkdir docker_setup
  cd docker_setup
  gsutil -m cp "${DEP_BUCKET}/${ORACLE_RPM}" ./
  git clone "${ORACLE_DOCKER_REPO}"
  cp docker-images/OracleDatabase/SingleInstance/dockerfiles/11.2.0.2/* ./
  rm -rf docker-images
else
  cd docker_setup
fi

echo "Attempting to stop any running docker images"
docker stop "${DOCKER_NAME}" || :
docker rm "${DOCKER_NAME}" || :
echo "Building new docker container"
docker build --shm-size=4g -t "${DOCKER_NAME}" -f Dockerfile.xe .
echo "Running new docker container"
docker run -itd --shm-size=1g --name "${DOCKER_NAME}" -p 1521:1521 -p 8080:8080 -e ORACLE_PWD=$1 "${DOCKER_NAME}"

echo "Waiting for DB to come up..."
sleep 90

echo "Configuring DB..."
docker cp ../setup_db.sh oracle-xe:/tmp/setup_db.sh
docker exec oracle-xe /bin/bash -c "/tmp/setup_db.sh $CUE_DB_USER $2"


if [ "$3" = "--build-prod" ]; then
  echo "Applying Schema..."
  docker exec oracle-xe /bin/bash -c "mkdir $(dirname $ORACLE_SQL_FILE)"
  docker cp ${CUEBOT_ROOT_DIRECTORY}/src/main/resources/conf/ddl/db-schema.sql oracle-xe:$ORACLE_SQL_FILE
  docker cp ${CUEBOT_ROOT_DIRECTORY}/oracle/xe/apply_schema.sh oracle-xe:/tmp/
  docker cp ${CUEBOT_ROOT_DIRECTORY}/oracle/xe/apply_schema.py oracle-xe:/tmp/
  docker exec oracle-xe /bin/bash -c "/tmp/apply_schema.sh $2 $CUE_DB_USER $ORACLE_SQL_FILE"
fi
