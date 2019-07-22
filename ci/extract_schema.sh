#!/bin/bash

set -e

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <BUILD_ID> <ARTIFACT_DIRECTORY>"
  exit 1
fi

BUILD_ID=$1
ARTIFACT_DIRECTORY=$2

DB_USER=postgres
DB_NAME=cuebot_extract_${BUILD_ID}
PG_CONTAINER=postgres-${BUILD_ID}
FLYWAY_CONTAINER=flyway-${BUILD_ID}
SCHEMA_DIRECTORY="$(pwd)/cuebot/src/main/resources/conf/ddl/postgres"

# Use migrations to populate a temporary database, then dump the full schema.
docker pull postgres
docker pull boxfuse/flyway
docker run --rm --name ${PG_CONTAINER} -d postgres
sleep 10
PG_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${PG_CONTAINER})
docker exec -t --user=${DB_USER} ${PG_CONTAINER} createdb ${DB_NAME}
docker run -td --rm --name ${FLYWAY_CONTAINER} --entrypoint bash boxfuse/flyway
docker cp ${SCHEMA_DIRECTORY}/migrations/* ${FLYWAY_CONTAINER}:/flyway/sql/
docker exec -t ${FLYWAY_CONTAINER} flyway -url=jdbc:postgresql://${PG_IP}/${DB_NAME} -user=${DB_USER} -n migrate
docker exec -t --user=${DB_USER} ${PG_CONTAINER} pg_dump --no-privileges --no-owner -s ${DB_NAME} \
    | tee "${ARTIFACT_DIRECTORY}/schema-${BUILD_ID}.sql"

# The demo data gets its own build artifact too.
cp "${SCHEMA_DIRECTORY}/demo_data.sql" "${ARTIFACT_DIRECTORY}/demo_data-${BUILD_ID}.sql"

docker kill ${FLYWAY_CONTAINER}
docker kill ${PG_CONTAINER}

