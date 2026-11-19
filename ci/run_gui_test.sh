#!/bin/bash

# Wrapper script for CueGUI tests.
#
# pytest's own exit code decides the result, recorded inside the xvfb session because
# xvfb-run sometimes crashes on exit after the tests have passed.

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

# os._exit skips interpreter teardown, which can segfault in Qt after a passing run. It can go
# once the test suite owns its QApplication lifecycle.
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
