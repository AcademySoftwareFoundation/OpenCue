#!/bin/bash

set -e

until nc --send-only $PGHOST $PGPORT < /dev/null
do
    echo "Waiting for postgres container..."
    sleep 2
done

until psql -w -c "select 1"
do
    echo "Waiting for postgres to accept connections..."
    sleep 2
done

echo "Applying database migrations..."
./flyway migrate -user=${PGUSER} -password=${PGPASSWORD} -url="jdbc:postgresql://${PGHOST}:${PGPORT}/${PGDATABASE}" -locations='filesystem:/opt/migrations'

# Check if a show exists, if not apply demo data
if psql -c "select 1 from show"|grep "(0 rows)"; then
    psql -a -f /opt/scripts/seed_data.sql
fi
