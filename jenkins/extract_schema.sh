#!/bin/sh

set -e

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

BUILD_ID=$1
ARTIFACT_DIRECTORY=$2

DB_USER=postgres
DB_NAME=cuebot_extract_$BUILD_ID
HOST_PORT=$(shuf -i 10000-20000 -n 1)
PG_CONTAINER=postgres-$BUILD_ID
SCHEMA_DIRECTORY="$(pwd)/cuebot/src/main/resources/conf/ddl/postgres"

docker pull postgres
docker pull boxfuse/flyway
docker run --rm --name $PG_CONTAINER -d -p $HOST_PORT:5432 postgres
sleep 10
docker exec -t --user=$DB_USER $PG_CONTAINER createdb $DB_NAME
docker run --rm -v "${SCHEMA_DIRECTORY}/migrations:/flyway/sql" boxfuse/flyway -url=jdbc:postgresql://localhost:$HOST_PORT/$DB_NAME -user=$DB_USER migrate
docker exec -t --user=$DB_USER $PG_CONTAINER pg_dump --no-privileges --no-owner -s cuebot_extract | tee "${ARTIFACT_DIRECTORY}/schema-${BUILD_ID}.sql"

cp "${SCHEMA_DIRECTORY}/demo_data.sql" "${ARTIFACT_DIRECTORY}/demo_data-${BUILD_ID}.sql"

