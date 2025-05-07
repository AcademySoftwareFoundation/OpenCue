#!/bin/bash
#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# OpenCue integration test script
#
# Stands up a clean environment using Docker compose and verifies all
# components are functioning as expected.
#
# Run with:
#   ./run_integration_test.sh

set -e

RQD_ROOT="/tmp/rqd"
TEST_LOGS="/tmp/opencue-test"
DOCKER_COMPOSE_LOG="${TEST_LOGS}/docker-compose.log"
DB_DATA_DIR="sandbox/db-data"
VENV="/tmp/opencue-integration-venv"

log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") $1 $2"
}

kill_descendant_processes() {
    local pid="$1"
    local and_self="${2:-false}"
    if children="$(pgrep -P "$pid")"; then
        for child in $children; do
            kill_descendant_processes "$child" true
        done
    fi
    if [[ "$and_self" == true ]]; then
        kill "$pid" 2>/dev/null || true
    fi
}

verify_command_exists() {
    if ! command -v $1 &> /dev/null; then
        log ERROR "command \"$1\" was not found"
        exit 1
    fi
}

verify_no_database() {
    if [ -e "${DB_DATA_DIR}" ]; then
        log ERROR "Postgres data directory ${DB_DATA_DIR} already exists"
        exit 1
    fi
}

verify_no_containers() {
    num_containers=$(docker compose ps --format json | jq length)
    if [[ $num_containers -gt 0 ]]; then
       log ERROR "Found ${num_containers} Docker compose containers, clean these up with \`docker compose rm\` before continuing"
       exit 1
    fi
}

create_rqd_root() {
  if [ -e "$RQD_ROOT" ]; then
    log ERROR "log root ${RQD_ROOT} already exists"
    exit 1
  fi

  mkdir -p "${RQD_ROOT}/logs"
  mkdir "${RQD_ROOT}/shots"
}

wait_for_service_state() {
    log INFO "Waiting for service \"$1\" to have state \"$2\"..."
    while true; do
        current_time=$(date +%s)
        if [[ $current_time -gt $3 ]]; then
            log ERROR "Timed out waiting for Docker compose to come up"
            exit 1
        fi
        container=$(docker compose ps --all --format json | jq -s ".[] | select(.Service==\"$1\")")
        if [[ ${container} = "" ]]; then
            log INFO "Service \"$1\": no container yet"
        else
            container_name=$(echo "$container" | jq -r '.Name')
            current_state=$(echo "$container" | jq -r '.State')
            log INFO "Service \"$1\": container \"${container_name}\" state = ${current_state}"
            if [[ ${current_state} = $2 ]]; then
                break
            fi
        fi
        sleep 5
    done
}

verify_flyway_success() {
    container=$(docker compose ps --all --format json | jq -s '.[] | select(.Service=="flyway")')
    container_name=$(echo "$container" | jq -r '.Name')
    exit_code=$(echo "$container" | jq -r '.ExitCode')
    if [[ ${exit_code} = 0 ]]; then
        log INFO "Service \"flyway\": container \"${container_name}\" exit code = 0 (PASS)"
    else
        log ERROR "Service \"flyway\": container \"${container_name}\" exit code = ${exit_code} (FAIL)"
        exit 1
    fi
}

verify_migration_versions() {
    migrations_in_db=$(docker compose exec -e PGUSER=cuebot db psql -Aqtc "SELECT COUNT(*) FROM flyway_schema_history")
    migrations_in_code=$(ls cuebot/src/main/resources/conf/ddl/postgres/migrations/ | wc -l | tr -d ' ')
    if [[ ${migrations_in_db} = ${migrations_in_code} ]]; then
        log INFO "Database and code both contain ${migrations_in_db} migrations (PASS)"
    else
        log ERROR "Database contains ${migrations_in_db} migrations, code contains ${migrations_in_code} (FAIL)"
        exit 1
    fi
}

create_and_activate_venv() {
    if [[ -d "${VENV}" ]]; then
        rm -rf "${VENV}"
    fi
    python3 -m venv "${VENV}"
    source "${VENV}/bin/activate"
}

test_pycue() {
    want_shows="['testing']"
    got_shows=$(python -c 'import opencue; print([show.name() for show in opencue.api.getShows()])')
    if [[ "${got_shows}" = "${want_shows}" ]]; then
        log INFO "(pycue) Got expected show list (PASS)"
    else
        log ERROR "(pycue) Got unexpected show list (FAIL)"
        log ERROR "got: ${got_shows}, want: ${want_shows}"
        exit 1
    fi

    rqd_ip=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' opencue-rqd-1)
    want_hosts="['${rqd_ip}']"
    got_hosts=$(python -c 'import opencue; print([host.name() for host in opencue.api.getHosts()])')
    if [[ "${got_hosts}" = "${want_hosts}" ]]; then
        log INFO "(pycue) Got expected host list (PASS)"
    else
        log ERROR "(pycue) Got unexpected host list (FAIL)"
        log ERROR "got: ${got_hosts}, want: ${want_hosts}"
        exit 1
    fi
}

test_cueadmin() {
    want_show="testing"
    ls_response=$(cueadmin -ls)
    got_show=$(echo "${ls_response}" | tail -n 1 | cut -d ' ' -f 1)
    if [[ "${got_show}" = "${want_show}" ]]; then
        log INFO "(cueadmin) Got expected -ls response (PASS)"
    else
        log ERROR "(cueadmin) Got unexpected -ls response (FAIL)"
        log ERROR "got show: ${got_show}, want show: ${want_show}"
        log ERROR "full response: ${ls_response}"
        exit 1
    fi

    want_host=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' opencue-rqd-1)
    lh_response=$(cueadmin -lh)
    got_host=$(echo "${lh_response}" | tail -n 1 | cut -d ' ' -f 1)
    if [[ "${got_host}" = "${want_host}" ]]; then
        log INFO "(cueadmin) Got expected -lh response (PASS)"
    else
        log ERROR "(cueadmin) Got unexpected -lh response (FAIL)"
        log ERROR "got host: ${got_host}, want host: ${want_host}"
        log ERROR "full response: ${lh_response}"
        exit 1
    fi
}

run_job() {
    samples/pyoutline/basic_job.py
    job_name="testing-shot01-${USER}_basic_job"
    samples/pycue/wait_for_job.py "${job_name}" --timeout 300
    log INFO "Job succeeded (PASS)"
}

cleanup() {
    docker compose rm --stop --force >>"${DOCKER_COMPOSE_LOG}" 2>&1
    rm -rf "${RQD_ROOT}" || true
    rm -rf "${DB_DATA_DIR}" || true
    rm -rf "${VENV}" || true
}

main() {
    # Ensure all subshells in the background are terminated when the main script exits.
    trap "{ kill_descendant_processes $$; exit; }" SIGINT SIGTERM EXIT

    mkdir -p "${TEST_LOGS}"
    if [[ "${CI:-false}" == true ]]; then
        log INFO "More logs can be found under the test-logs artifact attached to this workflow execution"
    else
        log INFO "More logs can be found at ${TEST_LOGS}"
    fi

    CI_DIRECTORY=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
    OPENCUE_ROOT=$(dirname "${CI_DIRECTORY}")
    log INFO "OpenCue project is located at ${OPENCUE_ROOT}"
    cd "${OPENCUE_ROOT}"

    verify_command_exists docker
    verify_command_exists "docker compose"
    verify_command_exists jq
    verify_no_database
    verify_no_containers
    create_rqd_root

    log INFO "$(docker --version)"
    log INFO "$(docker compose version)"

    log INFO "Building Cuebot image..."
    docker build -t opencue/cuebot -f cuebot/Dockerfile . &>"${TEST_LOGS}/docker-build-cuebot.log"
    if [[ ! -e "${OPENCUE_PROTO_PACKAGE_PATH}" ]]; then
      rm -rf proto/dist/*.*
      python -m build proto
      OPENCUE_PROTO_PACKAGE_PATH=$(ls -1 proto/dist/*.tar.gz)
      export OPENCUE_PROTO_PACKAGE_PATH
    fi
    if [[ ! -e "${OPENCUE_RQD_PACKAGE_PATH}" ]]; then
      rm -rf rqd/dist/*.*
      python -m build rqd
      OPENCUE_RQD_PACKAGE_PATH=$(ls -1 rqd/dist/*.tar.gz)
      export OPENCUE_RQD_PACKAGE_PATH
    fi
    log INFO "Building RQD image..."
    docker build --build-arg OPENCUE_PROTO_PACKAGE_PATH="${OPENCUE_PROTO_PACKAGE_PATH}" \
           --build-arg OPENCUE_RQD_PACKAGE_PATH="${OPENCUE_RQD_PACKAGE_PATH}" \
           -t opencue/rqd -f rqd/Dockerfile . &>"${TEST_LOGS}/docker-build-rqd.log"

    log INFO "Starting Docker compose..."
    docker compose up &>"${DOCKER_COMPOSE_LOG}" &
    if [[ "$(uname -s)" == "Darwin" ]]; then
        docker_timeout=$(date -v +5M +%s)
    else
        docker_timeout=$(date -d '5 min' +%s)
    fi
    wait_for_service_state "db" "running" $docker_timeout
    wait_for_service_state "flyway" "exited" $docker_timeout
    wait_for_service_state "cuebot" "running" $docker_timeout
    wait_for_service_state "rqd" "running" $docker_timeout

    verify_flyway_success
    verify_migration_versions
    log INFO "Creating Python virtual environment..."
    create_and_activate_venv
    log INFO "Installing OpenCue Python libraries..."
    sandbox/install-client-sources.sh
    log INFO "Testing pycue library..."
    test_pycue
    log INFO "Testing cueadmin..."
    test_cueadmin

    run_job

    cleanup

    log INFO "Success"
}

main
