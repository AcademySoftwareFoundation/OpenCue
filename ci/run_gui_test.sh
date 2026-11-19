#!/bin/bash

# Wrapper script for CueGUI tests.
#
# Python (in Qt teardown) and xvfb-run sometimes crash on exit after the tests have passed.
# pytest's own exit code decides the result: the interpreter leaves through os._exit right
# after pytest returns, and the code is recorded inside the xvfb session.

set -eo pipefail

py="$(command -v python3)"
if [[ -z "$py" ]]; then
  py="$(command -v python)"
fi
echo "Using Python binary ${py}"

if [[ -n "${OPENCUE_CUEGUI_PACKAGE_PATH:-}" ]]
then
  echo "Installing pre-built opencue_cuegui package"
  "${py}" -m pip install "${OPENCUE_CUEGUI_PACKAGE_PATH}[test]"
else
  "${py}" -m pip install ./cuegui[test]
fi

pytest_status="$(mktemp)"

# Fix for debian version of xvfb-run
source /etc/os-release
XVFB_RUN_ARG="-d"
if [[ $ID_LIKE == *debian* ]]
then
  XVFB_RUN_ARG="-a"
fi

run_pytest='import os, sys, pytest
rc = int(pytest.main(["cuegui"]))
sys.stdout.flush()
sys.stderr.flush()
os._exit(rc)'

xvfb-run $XVFB_RUN_ARG bash -c '"$1" -c "$3"; echo $? > "$2"' _ "${py}" "${pytest_status}" "${run_pytest}" \
  || echo "xvfb-run exited with status $?"

status="$(cat "${pytest_status}")"
if [[ "${status}" != 0 ]]; then
  echo "CueGUI tests failed (pytest exit code: ${status:-none})"
  exit 1
fi
echo "CueGUI tests passed"
