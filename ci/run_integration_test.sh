#!/bin/bash

set -e

RQD_ROOT="/tmp/rqd"
TEST_LOGS="/tmp/opencue_test"
DOCKER_COMPOSE_LOG="${TEST_LOGS}/docker_compose.log"

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
    db_data="sandbox/db-data"
    if [ -e "${db_data}" ]; then
        log ERROR "Postgres data directory ${db_data} already exists"
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
        docker compose ps -a
        docker compose ps -a --format json
        container=$(docker compose ps -a --format json | jq ".[] | select(.Service==\"$1\")")
        echo "${container}"
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
    container=$(docker compose ps --format json | jq '.[] | select(.Service=="flyway")')
    container_name=$(echo "$container" | jq -r '.Name')
    exit_code=$(echo "$container" | jq -r '.ExitCode')
    if [[ ${exit_code} = 0 ]]; then
        log INFO "Service \"flyway\": container \"${container_name}\" exit code = 0 (PASS)"
    else
        log ERROR "Service \"flyway\": container \"${container_name}\" exit code = ${exit_code} (FAIL)"
        exit 1
    fi
}

cleanup() {
    docker compose rm --stop --force >>"${DOCKER_COMPOSE_LOG}" 2>&1
    #docker compose rm --stop --force
    rm -rf "${RQD_ROOT}"
    rm -rf "sandbox/db-data"
}

main() {
    # Ensure all subshells in the background are terminated when the main script exits.
    trap "{ kill_descendant_processes $$; exit; }" SIGINT SIGTERM EXIT

    CI_DIRECTORY=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
    OPENCUE_ROOT=$(dirname "${CI_DIRECTORY}")
    log INFO "OpenCue project is located at ${OPENCUE_ROOT}"
    cd "${OPENCUE_ROOT}"

    verify_command_exists docker
    verify_command_exists "docker compose"
    verify_no_database
    verify_no_containers
    create_rqd_root

    log INFO "$(docker --version)"
    log INFO "$(docker compose version)"

    mkdir -p "${TEST_LOGS}"

    log INFO "Starting Docker compose..."
    docker compose up &>"${DOCKER_COMPOSE_LOG}" &
    #docker compose up &

    wait_for_service_state "db" "running"
    wait_for_service_state "flyway" "exited"
    wait_for_service_state "cuebot" "running"
    wait_for_service_state "rqd" "running"

    verify_flyway_success
    # TODO: Verify database is at current migration version.
    # TODO: Verify Cuebot process is running.
    # TODO: Verify RQD process is running.
    # TODO: Verify RQD host exists in the database.
    # TODO: Install pycue.
    # TODO: Verify fetching shows and hosts via pycue.

    cleanup

    log INFO "More logs can be found at ${TEST_LOGS}"
}

main
